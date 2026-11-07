import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import select, update
from .models import DB, Video, now
from .config import settings
from .providers import submit_video, poll_video, download_video

log = logging.getLogger(__name__)
SIZES = {'9:16': (720, 1280), '1:1': (720, 720), '16:9': (1280, 720)}


async def ffmpeg(*args):
    process = await asyncio.create_subprocess_exec('ffmpeg', '-nostdin', '-y', '-v', 'error', *args,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    try:
        _, error = await asyncio.wait_for(process.communicate(), 180)
    except BaseException:
        process.kill()
        await process.wait()
        raise
    if process.returncode:
        log.error('ffmpeg failed: %s', error.decode()[-2000:])
        raise ValueError('Video processing failed. Check the server logs.')


async def change(id, **values):
    async with DB() as db:
        await db.execute(update(Video).where(Video.id == id).values(**values, updated_at=now()))
        await db.commit()


async def process(video):
    target = settings.data_dir / f'{video.id}.mp4'
    source = settings.data_dir / f'{video.id}.source.mp4'
    width, height = SIZES[video.ratio]
    try:
        if video.engine == 'local':
            from .local_video import render_local
            await render_local(video, target, (width, height), ffmpeg, change)
        elif video.demo:
            await change(video.id, progress=30)
            await ffmpeg('-f', 'lavfi', '-i', f'color=c=0x173f39:s={width}x{height}:r=24:d=5',
                         '-vf', "drawtext=text='STUDIO DEMO':fontcolor=white:fontsize=42:x=(w-tw)/2:y=(h-th)/2,drawtext=text='Sample export - no avatar or voice':fontcolor=white:fontsize=20:x=(w-tw)/2:y=h/2+65",
                         '-c:v', 'libx264', '-threads', '2', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target))
        else:
            if not video.provider_id:
                # Persist submission intent before calling a paid external API. If interrupted,
                # do not automatically submit again (the remote request may have succeeded).
                await change(video.id, attempts=1)
                if video.attempts:
                    raise ValueError('Submission was interrupted. Check D-ID before creating another render to avoid duplicate charges.')
                provider_id = await submit_video(video)
                await change(video.id, provider_id=provider_id, progress=20)
            else:
                provider_id = video.provider_id
            for tick in range(180):
                result = await poll_video(provider_id)
                if result.get('status') == 'done':
                    await change(video.id, progress=90)
                    await download_video(result['result_url'], source)
                    await ffmpeg('-i', str(source), '-vf',
                        f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x102923,setsar=1',
                        '-c:v', 'libx264', '-threads', '2', '-crf', '20', '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target))
                    break
                if result.get('status') in {'error', 'rejected', 'failed'}:
                    raise ValueError('D-ID could not render this video. Check your provider dashboard and avatar availability.')
                await change(video.id, progress=min(85, 25 + tick // 3))
                await asyncio.sleep(5)
            else:
                raise ValueError('Rendering timed out after 15 minutes. Check D-ID before resubmitting.')
        await change(video.id, status='completed', progress=100, filename=target.name, error=None)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.exception('Render failed for %s', video.id)
        # Never expose provider response bodies, signed URLs or credentials to the browser.
        message = str(exc) if isinstance(exc, ValueError) else ('Local rendering failed. Check the offline voice engine, FFmpeg and server logs.' if video.engine == 'local' else 'Provider or network request failed. Check server logs and provider status.')
        await change(video.id, status='failed', error=message[:500])
        target.unlink(missing_ok=True)
    finally:
        source.unlink(missing_ok=True)


async def run_worker():
    while True:
        try:
            async with DB() as db:
                # One process with a sequential worker is the supported deployment model.
                video = (await db.execute(select(Video).where(Video.status.in_(['queued', 'rendering'])).order_by(Video.created_at).limit(1))).scalar_one_or_none()
                if video:
                    await db.execute(update(Video).where(Video.id == video.id).values(status='rendering', updated_at=now()))
                    await db.commit()
            if video:
                await process(video)
            else:
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception('Worker iteration failed')
            await asyncio.sleep(5)
