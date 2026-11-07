"""Check an isolated production import, generated secret, HTTPS cookie, and static mount."""
import os
from pathlib import Path
import secrets
import subprocess
import sys


def test_single_origin_hosted_application(tmp_path):
    static=tmp_path/'static'
    static.mkdir()
    (static/'index.html').write_text('<html><body>Forma hosted dashboard</body></html>')
    environment=os.environ.copy()
    environment.pop('FRONTEND_ORIGIN',None)
    environment.update(APP_ENV='production', ADMIN_PASSWORD=secrets.token_urlsafe(24),
        ENCRYPTION_KEY='', ENCRYPTION_SEED=secrets.token_urlsafe(48),
        STATIC_DIR=str(static), DATA_DIR=str(tmp_path/'data'),
        DATABASE_URL=f'sqlite+aiosqlite:///{tmp_path}/hosted.db',
        RENDER_EXTERNAL_URL='https://hosted-test.onrender.com',GENERATION_MODE='local',DEMO_MODE='false',
        EPHEMERAL_STORAGE='true')
    script='''
import os
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app,base_url=os.environ['RENDER_EXTERNAL_URL']) as client:
    page=client.get('/')
    assert page.status_code==200 and 'Forma hosted dashboard' in page.text
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/workspace').status_code==401
    login=client.post('/api/login',json={'password':os.environ['ADMIN_PASSWORD']})
    assert login.status_code==200
    assert 'Secure' in login.headers['set-cookie'] and 'HttpOnly' in login.headers['set-cookie']
    workspace=client.get('/api/workspace')
    assert workspace.status_code==200
    assert workspace.json()['ephemeral_storage'] is True
    assert workspace.json()['generation_mode']=='local'
    assert client.post('/api/projects',json={},headers={'Origin':'https://evil.example'}).status_code==403
print('Hosted HTTPS configuration and dashboard/API routing verified.')
'''
    result=subprocess.run([sys.executable,'-c',script],env=environment,cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
