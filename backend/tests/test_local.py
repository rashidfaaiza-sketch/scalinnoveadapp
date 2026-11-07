import asyncio
import json
import os
import subprocess
import time
import wave
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.providers import generate_script
from app.schemas import GenerateIn
from app.speech import synthesize


@pytest.mark.parametrize('voice',['local-neutral','local-warm','local-bright'])
def test_offline_speech_has_nonzero_samples(voice,tmp_path):
    path=tmp_path/'speech.wav'
    synthesize('Your next great idea starts here.',voice,path)
    with wave.open(str(path),'rb') as output:
        assert output.getnframes()>1000
        assert any(output.readframes(output.getnframes()))


@pytest.mark.asyncio
async def test_local_scripts_never_use_paid_services(monkeypatch):
    monkeypatch.setattr(settings,'generation_mode','local')
    monkeypatch.setattr(settings,'demo_mode',False)
    def blocked(*args,**kwargs): raise AssertionError('Local mode must not call external providers')
    monkeypatch.setattr(httpx,'AsyncClient',blocked)
    project=SimpleNamespace(product='Loop Bottle',audience='daily commuters',objective='Drive signups')
    scripts=[]
    for tone in ['Confident','Friendly','Bold','Educational']:
        script=await generate_script(project,GenerateIn(tone=tone))
        assert project.product in script.hook
        assert project.audience in script.body
        assert 'sign up' in script.cta
        scripts.append(script.hook)
    assert len(set(scripts))==4
    youtube=await generate_script(project,GenerateIn(platform='YouTube'))
    assert len(youtube.body)>len(script.body)


@pytest.mark.parametrize('ratio,avatar,voice,size',[
    ('9:16','ava','local-neutral',(720,1280)),
    ('1:1','noah','local-warm',(720,720)),
    ('16:9','mia','local-bright',(1280,720)),
])
def test_cpu_video_with_real_audio_and_captions(monkeypatch,ratio,avatar,voice,size):
    monkeypatch.setattr(settings,'generation_mode','local')
    monkeypatch.setattr(settings,'demo_mode',False)
    monkeypatch.setattr(settings,'local_tts_engine','espeak')
    def blocked(*args,**kwargs): raise AssertionError('A free render attempted an external API call')
    monkeypatch.setattr(httpx,'AsyncClient',blocked)
    with TestClient(app) as client:
        assert client.post('/api/login',json={'password':'test-password-long-enough'}).status_code==200
        workspace=client.get('/api/workspace').json()
        assert workspace['generation_mode']=='local'
        assert all(v['id'].startswith('local-') for v in workspace['voices'])
        project=client.post('/api/projects',json={'name':'CPU test','product':'Loop','audience':'Creators','objective':'Introduce'}).json()
        script=client.post(f"/api/projects/{project['id']}/scripts",json={'hook':'Meet your next good idea.','body':'Create your own story with local narration.','cta':'Explore today.'}).json()
        response=client.post('/api/videos',json={'script_id':script['id'],'name':'Free character ad','ratio':ratio,'avatar':avatar,'voice':voice})
        assert response.status_code==202,response.text
        video_id=response.json()['id']
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            video=next(v for v in client.get('/api/workspace').json()['videos'] if v['id']==video_id)
            if video['status'] in {'completed','failed'}: break
            time.sleep(.2)
        assert video['status']=='completed',video
        assert video['engine']=='local' and video['demo'] is False
        path=settings.data_dir/video['filename']
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
        streams={stream['codec_type']:stream for stream in info['streams']}
        assert streams['video']['width']==size[0] and streams['video']['height']==size[1]
        assert streams['audio']['codec_name']=='aac'
        assert float(streams['audio']['duration'])>2
        assert 'Synthetic narration' in info['format']['tags']['comment']
        if ratio=='9:16':
            hashes=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-an','-vf','crop=120:120:300:540','-f','framemd5','-']).decode()
            # Crop only the mouth/face: caption changes cannot satisfy this check.
            assert len({line.split(',')[-1].strip() for line in hashes.splitlines() if line and not line.startswith('#')})>1
        assert client.get(f'/api/videos/{video_id}/file?download=true').status_code==200
        assert client.get('/api/settings').json()['providers']=={}


@pytest.mark.skipif(os.environ.get('RUN_LOUDKIT_MODEL_TEST')!='1',reason='Optional ~750 MB neural model download; run explicitly after choosing loudkit.')
def test_optional_loudkit_sentence(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'local_tts_engine','loudkit')
    path=tmp_path/'loudkit.wav'
    synthesize('Hello from the local studio.','local-neutral',path)
    assert path.stat().st_size>1000
