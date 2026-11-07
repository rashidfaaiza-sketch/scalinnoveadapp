import json
import subprocess
import time
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.models import DB, Credential
from app.config import settings


def sign_in(client):
    response = client.post('/api/login', json={'password':'test-password-long-enough'})
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']


def test_authentication_and_origin_controls():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        assert client.get('/api/workspace').status_code == 401
        assert client.post('/api/login', json={'password':'wrong-password'}).status_code == 401
        assert client.post('/api/login', json={'password':'test-password-long-enough'}, headers={'origin':'https://evil.example'}).status_code == 403
        assert client.post('/api/login', content='password=test', headers={'content-type':'application/x-www-form-urlencoded'}).status_code == 415
        sign_in(client)
        assert client.get('/api/workspace').status_code == 200
        assert client.post('/api/logout', json={}).status_code == 200
        assert client.get('/api/workspace').status_code == 401


def test_project_script_render_and_download():
    with TestClient(app) as client:
        sign_in(client)
        assert client.post('/api/projects', json={'name':''}).status_code == 422
        project = client.post('/api/projects', json={'name':'Launch campaign','product':'Everyday bottle','audience':'Busy commuters','objective':'Introduce reusable bottles'}).json()
        script = client.post(f"/api/projects/{project['id']}/generate", json={'platform':'Short-form','tone':'Friendly'}).json()
        assert script['hook'] and script['cta'] and script['project_id'] == project['id']
        script['hook'] = 'Your commute deserves a better bottle.'
        edited = client.put(f"/api/scripts/{script['id']}", json={key:script[key] for key in ['hook','body','cta','platform']})
        assert edited.status_code == 200
        for ratio, size in [('9:16',(720,1280)),('1:1',(720,720)),('16:9',(1280,720))]:
            response = client.post('/api/videos', json={'script_id':script['id'],'name':f'Launch {ratio}','ratio':ratio})
            assert response.status_code == 202
            video_id = response.json()['id']
            assert client.get(f'/api/videos/{video_id}/file').status_code == 409
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                video = next(v for v in client.get('/api/workspace').json()['videos'] if v['id'] == video_id)
                if video['status'] in {'completed','failed'}: break
                time.sleep(.3)
            assert video['status'] == 'completed', video
            assert video['progress'] == 100 and video['demo'] is True
            file = client.get(f'/api/videos/{video_id}/file?download=true')
            assert file.status_code == 200 and file.content[4:8] == b'ftyp'
            assert file.headers['content-type'] == 'video/mp4'
            assert 'attachment' in file.headers['content-disposition']
            partial = client.get(f'/api/videos/{video_id}/file', headers={'Range':'bytes=0-99'})
            assert partial.status_code == 206 and len(partial.content) == 100
            info = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(settings.data_dir / video['filename'])]))
            assert (info['streams'][0]['width'],info['streams'][0]['height']) == size
            assert client.patch(f'/api/videos/{video_id}', json={'name':'Final ad'}).json()['name'] == 'Final ad'
        assert client.post('/api/videos', json={'script_id':'missing','name':'Bad reference'}).status_code == 404
        assert client.post('/api/videos', json={'script_id':script['id'],'name':'Bad format','ratio':'2:3'}).status_code == 422
        assert client.get('/api/videos/missing/file').status_code == 404
        exported = client.post(f'/api/videos/{video_id}/exports', json={'ratio':'1:1'})
        assert exported.status_code == 200
        asset = client.get(exported.json()['url'])
        assert asset.status_code == 200 and asset.content[4:8] == b'ftyp'
        probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(settings.data_dir / f'{video_id}-1-1.mp4')]))
        assert probe['streams'][0]['width'] == probe['streams'][0]['height'] == 720
        assert client.post(f'/api/videos/{video_id}/exports', json={'ratio':'1:1'}).json() == exported.json()
        assert client.get(f'/api/videos/{video_id}/file?ratio=invalid').status_code == 422


def test_key_storage_is_encrypted_and_never_returned():
    with TestClient(app) as client:
        sign_in(client)
        raw = 'test-provider-secret-value'
        assert client.put('/api/settings/keys/openai', json={'key':raw}).status_code == 200
        metadata = client.get('/api/settings')
        assert metadata.json()['providers']['openai'] is True
        assert raw not in metadata.text and raw not in client.get('/api/workspace').text
        async def stored():
            async with DB() as db: return (await db.get(Credential,'openai')).encrypted
        assert raw not in asyncio.run(stored())
        assert client.put('/api/settings/keys/unknown', json={'key':raw}).status_code == 404
        assert client.delete('/api/settings/keys/openai').json()['configured'] is False
