import asyncio
import time
from fastapi.testclient import TestClient
from app.main import app
from app.models import DB, Project, Script, Video


def test_interrupted_paid_submission_is_not_repeated():
    # Simulate a database restored after POST submission intent was persisted,
    # but before the provider response could be recorded.
    async def seed():
        async with DB() as db:
            project = Project(name='Recovery',product='Test',audience='Test',objective='Test')
            db.add(project)
            await db.flush()
            script = Script(project_id=project.id,hook='Hello',body='Story',cta='Go',platform='Short-form')
            db.add(script)
            await db.flush()
            video = Video(project_id=project.id,script_id=script.id,name='Interrupted',text='Hello Story Go',avatar='ava',voice='en-US-JennyNeural',ratio='9:16',expression='natural',demo=False,status='rendering',attempts=1)
            db.add(video)
            await db.commit()
            return video.id
    with TestClient(app) as client:
        video_id = asyncio.run(seed())
    # A new lifespan must recover the job from the database, not in-memory state.
    with TestClient(app) as client:
        assert client.post('/api/login',json={'password':'test-password-long-enough'}).status_code == 200
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            video = next(v for v in client.get('/api/workspace').json()['videos'] if v['id'] == video_id)
            if video['status'] == 'failed': break
            time.sleep(.2)
        assert video['status'] == 'failed'
        assert 'duplicate charges' in video['error']
        assert client.get(f'/api/videos/{video_id}/file').status_code == 409
