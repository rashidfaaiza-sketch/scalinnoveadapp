import asyncio
import hashlib
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, func, inspect, text
from .config import settings
from .models import Base, engine, DB, Project, Script, Video, Credential, Session
from .schemas import ProjectIn, ScriptIn, GenerateIn, RenderIn, RenameIn, KeyIn, LoginIn, ExportIn, serialize
from .providers import AVATARS, VOICES, generate_script, get_key
from .worker import run_worker, ffmpeg, SIZES

settings.validate_runtime()
password_hasher = PasswordHasher()
password_hash = password_hasher.hash(settings.admin_password)
limits = defaultdict(deque)
export_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        columns = await connection.run_sync(lambda conn: {c['name'] for c in inspect(conn).get_columns('videos')})
        if 'engine' not in columns:
            # Additive upgrade keeps historical paid/demo jobs on their original pipeline.
            await connection.execute(text("ALTER TABLE videos ADD COLUMN engine VARCHAR(20) NOT NULL DEFAULT 'provider'"))
    worker = asyncio.create_task(run_worker())
    yield
    worker.cancel()
    with suppress(asyncio.CancelledError):
        await worker
    await engine.dispose()


app = FastAPI(title='Forma Studio API', version='1.0.0', lifespan=lifespan,
              docs_url='/api/docs' if settings.app_env != 'production' else None,
              redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'], allow_headers=['Content-Type'])


@app.middleware('http')
async def security(request: Request, call_next):
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        origin = request.headers.get('origin')
        if origin and origin != settings.frontend_origin:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Origin is not allowed'}, status_code=403)
        # JSON-only mutations prevent cross-site HTML form submissions.
        if request.method in {'POST', 'PUT', 'PATCH'} and 'application/json' not in request.headers.get('content-type', ''):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'application/json is required'}, status_code=415)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers['Cache-Control'] = 'no-store'
    return response


def rate_limit(request, bucket, count, seconds):
    key = (request.client.host if request.client else 'unknown', bucket)
    current = time.monotonic()
    if len(limits) > 10000:
        for old_key in list(limits):
            if not limits[old_key] or limits[old_key][-1] < current - 3600:
                del limits[old_key]
    timestamps = limits[key]
    while timestamps and timestamps[0] <= current - seconds:
        timestamps.popleft()
    if len(timestamps) >= count:
        raise HTTPException(429, 'Too many requests. Try again shortly.', headers={'Retry-After': str(seconds)})
    timestamps.append(current)


async def auth(request: Request):
    token = request.cookies.get('studio_session', '')
    async with DB() as db:
        session = await db.get(Session, hashlib.sha256(token.encode()).hexdigest())
        if not session or session.expires_at <= time.time():
            raise HTTPException(401, 'Please sign in to your workspace.')


async def required(db, model, id):
    item = await db.get(model, id)
    if not item:
        raise HTTPException(404, 'This item no longer exists.')
    return item


@app.get('/api/health')
async def health():
    async with DB() as db:
        await db.execute(select(1))
    return {'status': 'ok'}


@app.post('/api/login')
async def login(data: LoginIn, request: Request, response: Response):
    rate_limit(request, 'login', 10, 300)
    try:
        await asyncio.to_thread(password_hasher.verify, password_hash, data.password)
    except VerifyMismatchError:
        raise HTTPException(401, 'Incorrect workspace password.')
    token = secrets.token_urlsafe(48)
    async with DB() as db:
        await db.execute(delete(Session).where(Session.expires_at < time.time()))
        db.add(Session(token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=time.time() + settings.session_hours * 3600))
        await db.commit()
    response.set_cookie('studio_session', token, httponly=True, secure=settings.app_env == 'production',
                        samesite='strict', max_age=settings.session_hours * 3600, path='/api')
    return {'ok': True}


@app.post('/api/logout', dependencies=[Depends(auth)])
async def logout(request: Request, response: Response):
    async with DB() as db:
        await db.execute(delete(Session).where(Session.token_hash == hashlib.sha256(request.cookies.get('studio_session', '').encode()).hexdigest()))
        await db.commit()
    response.delete_cookie('studio_session', path='/api')
    return {'ok': True}


@app.get('/api/workspace', dependencies=[Depends(auth)])
async def workspace():
    async with DB() as db:
        projects = (await db.scalars(select(Project).order_by(Project.created_at.desc()))).all()
        scripts = (await db.scalars(select(Script).order_by(Script.created_at.desc()))).all()
        videos = (await db.scalars(select(Video).order_by(Video.created_at.desc()))).all()
    from .speech import VOICES as LOCAL_VOICES
    voices = LOCAL_VOICES if settings.generation_mode == 'local' else VOICES
    if settings.generation_mode == 'local' and settings.local_tts_engine == 'loudkit':
        voices = [{'id': 'local-neutral', 'name': 'Joe', 'description': 'English · Optional loudkit neural voice'}]
    return {'projects': [serialize(x) for x in projects], 'scripts': [serialize(x) for x in scripts],
            'videos': [serialize(x) for x in videos], 'demo_mode': settings.demo_mode and settings.generation_mode == 'provider', 'generation_mode': settings.generation_mode, 'tts_engine': settings.local_tts_engine, 'ephemeral_storage': settings.ephemeral_storage, 'avatars': AVATARS, 'voices': voices}


@app.post('/api/projects', dependencies=[Depends(auth)], status_code=201)
async def create_project(data: ProjectIn):
    async with DB() as db:
        project = Project(**data.model_dump())
        db.add(project)
        await db.commit()
        return serialize(project)


@app.post('/api/projects/{id}/generate', dependencies=[Depends(auth)], status_code=201)
async def generate(id: str, data: GenerateIn, request: Request):
    rate_limit(request, 'generate', 15, 60)
    async with DB() as db:
        project = await required(db, Project, id)
        try:
            result = await generate_script(project, data)
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:300])
        except Exception:
            raise HTTPException(502, 'Script provider request failed. Verify your API key, model access and provider balance.')
        script = Script(project_id=id, **result.model_dump())
        db.add(script)
        await db.commit()
        return serialize(script)


@app.post('/api/projects/{id}/scripts', dependencies=[Depends(auth)], status_code=201)
async def save_script(id: str, data: ScriptIn):
    async with DB() as db:
        await required(db, Project, id)
        script = Script(project_id=id, **data.model_dump())
        db.add(script)
        await db.commit()
        return serialize(script)


@app.put('/api/scripts/{id}', dependencies=[Depends(auth)])
async def edit_script(id: str, data: ScriptIn):
    async with DB() as db:
        script = await required(db, Script, id)
        for key, value in data.model_dump().items():
            setattr(script, key, value)
        await db.commit()
        return serialize(script)


@app.post('/api/videos', dependencies=[Depends(auth)], status_code=202)
async def render(data: RenderIn, request: Request):
    rate_limit(request, 'render', 10, 60)
    if settings.generation_mode == 'provider' and data.voice.startswith('local-'):
        raise HTTPException(422, 'Choose a provider voice before using the paid pipeline.')
    if settings.generation_mode == 'provider' and not settings.demo_mode and not await get_key('did'):
        raise HTTPException(422, 'Add a D-ID API key in Settings before rendering.')
    async with DB() as db:
        active = await db.scalar(select(func.count()).select_from(Video).where(Video.status.in_(['queued', 'rendering'])))
        if active >= 20:
            raise HTTPException(429, 'The render queue is full. Wait for an active job to finish.')
        script = await required(db, Script, data.script_id)
        spoken = ' '.join([script.hook, script.body, script.cta])
        if settings.generation_mode == 'local' and len(spoken.split()) > 220:
            raise HTTPException(422, 'Local ads support up to 220 spoken words. Shorten the script before rendering.')
        video = Video(**data.model_dump(), project_id=script.project_id, text=spoken, demo=settings.demo_mode if settings.generation_mode == 'provider' else False, engine=settings.generation_mode)
        db.add(video)
        await db.commit()
        return serialize(video)


@app.patch('/api/videos/{id}', dependencies=[Depends(auth)])
async def rename(id: str, data: RenameIn):
    async with DB() as db:
        video = await required(db, Video, id)
        video.name = data.name
        await db.commit()
        return serialize(video)


@app.get('/api/videos/{id}/file', dependencies=[Depends(auth)])
async def video_file(id: str, download: bool = False, ratio: Literal["9:16", "1:1", "16:9"] | None = None):
    async with DB() as db:
        video = await required(db, Video, id)
        if video.status != 'completed' or not video.filename:
            raise HTTPException(409, 'This video is not ready yet.')
        path = settings.data_dir / (f"{video.id}-{ratio.replace(':', '-')}.mp4" if ratio and ratio != video.ratio else video.filename)
        if not path.is_file():
            raise HTTPException(404, 'Video file is missing. Restore your media volume backup.')
        return FileResponse(path, media_type='video/mp4', filename=f'forma-{video.id}.mp4' if download else None,
                            content_disposition_type='attachment' if download else 'inline')


@app.get('/api/settings', dependencies=[Depends(auth)])
async def get_settings():
    return {'demo_mode': settings.demo_mode and settings.generation_mode == 'provider', 'generation_mode': settings.generation_mode, 'tts_engine': settings.local_tts_engine, 'providers': {provider: bool(await get_key(provider)) for provider in ['openai', 'did']} if settings.generation_mode == 'provider' else {}}


@app.put('/api/settings/keys/{provider}', dependencies=[Depends(auth)])
async def set_key(provider: str, data: KeyIn):
    if provider not in {'openai', 'did'}:
        raise HTTPException(404, 'Unknown provider')
    encrypted = Fernet(settings.encryption_key.encode()).encrypt(data.key.strip().encode()).decode()
    async with DB() as db:
        credential = await db.get(Credential, provider)
        if credential:
            credential.encrypted = encrypted
        else:
            db.add(Credential(provider=provider, encrypted=encrypted))
        await db.commit()
    return {'configured': True}


@app.delete('/api/settings/keys/{provider}', dependencies=[Depends(auth)])
async def delete_key(provider: str):
    if provider not in {'openai', 'did'}:
        raise HTTPException(404, 'Unknown provider')
    async with DB() as db:
        await db.execute(delete(Credential).where(Credential.provider == provider))
        await db.commit()
    return {'configured': bool(await get_key(provider))}


@app.post('/api/videos/{id}/exports', dependencies=[Depends(auth)])
async def export_video(id: str, data: ExportIn, request: Request):
    rate_limit(request, 'export', 10, 60)
    async with DB() as db:
        video = await required(db, Video, id)
        if video.status != 'completed' or not video.filename:
            raise HTTPException(409, 'This video is not ready yet.')
        source = settings.data_dir / video.filename
        if not source.is_file():
            raise HTTPException(404, 'The source video is missing.')
        if data.ratio != video.ratio:
            target = settings.data_dir / f"{video.id}-{data.ratio.replace(':', '-')}.mp4"
            async with export_lock:
                if not target.exists():
                    temp = target.with_suffix('.partial.mp4')
                    width, height = SIZES[data.ratio]
                    try:
                        await ffmpeg('-i', str(source), '-vf',
                            f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x102923,setsar=1',
                            '-c:v', 'libx264', '-threads', '2', '-crf', '20', '-c:a', 'aac', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temp))
                        temp.replace(target)
                    except ValueError:
                        raise HTTPException(500, 'Export processing failed. Check server logs.')
                    finally:
                        temp.unlink(missing_ok=True)
        return {'url': f'/api/videos/{video.id}/file?download=true&ratio={data.ratio}'}


# Mount after /api routes: one origin serves the dashboard and authenticated API.
if settings.static_dir is not None:
    app.mount('/', StaticFiles(directory=settings.static_dir, html=True), name='dashboard')
