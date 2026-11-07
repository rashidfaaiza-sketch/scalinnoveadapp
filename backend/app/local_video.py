"""CPU-only illustrated ads with audio-reactive mouths and estimated caption timing."""
import array
import bisect
import math
import sys
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .speech import speak
from .config import settings

PALETTES = {
    'ava': ('#183e34', '#e8bc9a', '#49382f', '#e7a875'),
    'noah': ('#263d55', '#a86d4b', '#242626', '#b8c9a2'),
    'mia': ('#493856', '#dca083', '#3a2639', '#d9b8d2'),
}


def font(size):
    # Pillow wheels bundle a portable default TrueType font; prefer system DejaVu.
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


def wrapped(draw, text, typeface, width):
    lines, current = [], ''
    for word in text.split():
        # Wrap unusually long words too; user text never enters an FFmpeg filter expression.
        for part in [word[i:i+24] for i in range(0, len(word), 24)]:
            candidate = f'{current} {part}'.strip()
            if current and draw.textlength(candidate, font=typeface) > width:
                lines.append(current)
                current = part
            else:
                current = candidate
    if current:
        lines.append(current)
    return '\n'.join(lines)


def draw_character(draw, x, y, radius, avatar, mouth=0, blink=False):
    _, skin, hair, shirt = PALETTES[avatar]
    r = radius
    def box(a,b,c,d): return (x+a*r,y+b*r,x+c*r,y+d*r)
    # Original vector character artwork, not a photo or a realistic face clone.
    draw.ellipse(box(-1.45,-1.5,1.45,1.5), fill='#ffffff0a' if draw.mode == 'RGBA' else '#31594b')
    draw.rounded_rectangle(box(-1.35,.75,1.35,2), radius=int(r*.35), fill=shirt)
    draw.rounded_rectangle(box(-.28,.5,.28,1.05), radius=int(r*.1), fill=skin)
    draw.ellipse(box(-1.03,-1.27,1.03,1.1), fill=hair)
    draw.ellipse(box(-.9,-1,.9,1), fill=skin)
    draw.pieslice(box(-1.03,-1.3,1.02,.3),180,350,fill=hair)
    for side in (-1,1):
        ex=x+side*r*.34
        if blink:
            draw.line((ex-r*.13,y-r*.02,ex+r*.13,y-r*.02),fill=hair,width=max(2,int(r*.035)))
        else:
            draw.ellipse((ex-r*.06,y-r*.1,ex+r*.06,y+r*.035),fill=hair)
        draw.line((ex-r*.14,y-r*.26,ex+r*.12,y-r*.29),fill=hair,width=max(2,int(r*.035)))
    draw.arc(box(-.05,.04,.15,.35),5,150,fill='#875c50',width=max(1,int(r*.025)))
    if mouth:
        draw.ellipse(box(-.23,.40-.045*mouth,.23,.48+.11*mouth),fill='#532d35')
        draw.rounded_rectangle(box(-.16,.40,.16,.46),radius=2,fill='#fff0df')
    else:
        draw.arc(box(-.27,.30,.27,.58),0,180,fill='#733f43',width=max(2,int(r*.035)))


def frame(path, size, avatar, name, caption, mouth, blink):
    width,height=size
    background,*_=PALETTES[avatar]
    image=Image.new('RGB',size,background)
    draw=ImageDraw.Draw(image)
    unit=min(width,height)/720
    landscape=width>height
    draw.text((int(width*.07),int(height*.055)), 'FORMA / LOCAL STUDIO', font=font(int(16*unit)), fill='#c4d3ac')
    draw.text((int(width*.07),int(height*.11)),wrapped(draw,name[:60] + ('…' if len(name)>60 else ''),font(int(28*unit)),width*.86),font=font(int(28*unit)),fill='#f5f3df',spacing=6)
    x=width*.29 if landscape else width*.5
    y=height*.46 if landscape else height*.40
    radius=min(width*.23,height*.16)
    draw_character(draw,x,y,radius,avatar,mouth,blink)
    caption_box=(int(width*.54),int(height*.36),int(width*.93),int(height*.81)) if landscape else (int(width*.07),int(height*.74),int(width*.93),int(height*.93))
    left,top,right,bottom=caption_box
    draw.rounded_rectangle(caption_box,radius=int(18*unit),fill='#f0f2df')
    typeface=font(int(27*unit))
    content=wrapped(draw,caption,typeface,right-left-40*unit)
    for point_size in range(int(27*unit),13,-1):
        typeface=font(point_size)
        content=wrapped(draw,caption,typeface,right-left-40*unit)
        bounds=draw.multiline_textbbox((0,0),content,font=typeface,spacing=int(8*unit))
        if bounds[3]-bounds[1] < bottom-top-30*unit:
            break
    draw.multiline_text(((left+right)/2,(top+bottom)/2),content,font=typeface,fill='#233e35',anchor='mm',align='center',spacing=int(8*unit))
    draw.text((int(width*.07),int(height*.967)), 'SYNTHETIC VOICE / ILLUSTRATED CHARACTER', font=font(max(10,int(11*unit))),fill='#b6c6ad')
    image.save(path,compress_level=2)


def build_frames(audio, folder, size, video):
    with wave.open(str(audio),'rb') as source:
        if source.getsampwidth()!=2 or source.getnchannels()!=1:
            raise ValueError('Narration must be mono 16-bit PCM.')
        rate=source.getframerate()
        samples=array.array('h',source.readframes(source.getnframes()))
    if sys.byteorder != 'little': samples.byteswap()
    duration=len(samples)/rate
    if duration <= .1 or duration > 180:
        raise ValueError('Local narration must last between 0.1 seconds and three minutes.')
    words=video.text.split()
    captions=[' '.join(words[i:i+5]) for i in range(0,len(words),5)]
    weights=[sum(len(w)+1 for w in words[i:i+5]) for i in range(0,len(words),5)]
    cumulative=[]
    total=sum(weights)
    elapsed=0
    for weight in weights:
        elapsed+=weight/total*duration
        cumulative.append(elapsed)
    hop=max(1,int(rate/10))
    energy=[]
    for start in range(0,len(samples),hop):
        chunk=samples[start:start+hop]
        energy.append(math.sqrt(sum(v*v for v in chunk)/max(1,len(chunk))))
    maximum=max(energy) or 1
    cache={}
    lines=[]
    intensity={'natural':1,'lively':1.3,'serious':.7}[video.expression]
    for index,amplitude in enumerate(energy):
        t=index/10
        caption_index=min(len(captions)-1,bisect.bisect_right(cumulative,t))
        level=amplitude/maximum*intensity
        mouth=2 if level>.3 else 1 if level>.06 else 0
        blink=index%43 in (0,1)
        key=(caption_index,mouth,blink)
        if key not in cache:
            filename=f'frame-{len(cache):04d}.png'
            frame(folder/filename,size,video.avatar,video.name,captions[caption_index],mouth,blink)
            cache[key]=filename
        lines.extend([f"file '{cache[key]}'",f'duration {min(.1,duration-t):.6f}'])
    lines.append(f"file '{cache[key]}'")
    playlist=folder/'frames.txt'
    playlist.write_text('\n'.join(lines)+'\n')
    return playlist,duration


async def render_local(video,target,size,encode,progress):
    import asyncio
    with tempfile.TemporaryDirectory(prefix=f'local-{video.id}-',dir=settings.data_dir) as name:
        folder=Path(name)
        await progress(video.id,progress=10)
        raw=folder/'voice-original.wav'
        await speak(video.text,video.voice,raw)
        audio=folder/'narration.wav'
        await encode('-i',str(raw),'-ac','1','-ar','22050','-c:a','pcm_s16le',str(audio))
        await progress(video.id,progress=35)
        playlist,duration=await asyncio.to_thread(build_frames,audio,folder,size,video)
        await progress(video.id,progress=65)
        await encode('-f','concat','-safe','1','-i',str(playlist),'-i',str(audio),'-t',str(duration),
                     '-vf','fps=24','-c:v','libx264','-preset','veryfast','-threads','2','-crf','22',
                     '-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',
                     '-metadata','comment=Synthetic narration and audio-reactive illustrated character. Captions use estimated timing.',str(target))
