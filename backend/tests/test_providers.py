import httpx
import pytest
from types import SimpleNamespace
from app import providers
from app.schemas import GenerateIn


@pytest.mark.asyncio
async def test_live_script_payload_and_response(monkeypatch):
    monkeypatch.setattr(providers.settings, 'demo_mode', False)
    async def key(provider): return 'fake-key'
    async def request(client, method, url, **kwargs):
        assert method == 'POST' and url == 'https://api.openai.com/v1/chat/completions'
        assert kwargs['json']['response_format'] == {'type':'json_object'}
        return httpx.Response(200, json={'choices':[{'message':{'content':'{"hook":"A fresh start","body":"Meet your new routine.","cta":"Explore today."}'}}]})
    monkeypatch.setattr(providers, 'get_key', key)
    monkeypatch.setattr(providers, 'request', request)
    result = await providers.generate_script(SimpleNamespace(product='Bottle',audience='Commuters',objective='Awareness'), GenerateIn())
    assert result.hook == 'A fresh start'


@pytest.mark.asyncio
async def test_live_avatar_submission(monkeypatch):
    async def key(provider): return 'fake-basic-key'
    async def request(client, method, url, **kwargs):
        assert kwargs['headers']['Authorization'] == 'Basic fake-basic-key'
        assert kwargs['json']['script']['provider']['voice_id'] == 'en-US-JennyNeural'
        assert kwargs['json']['script']['input'] == 'Hello world'
        return httpx.Response(201, json={'id':'talk-test'})
    monkeypatch.setattr(providers, 'get_key', key)
    monkeypatch.setattr(providers, 'request', request)
    assert await providers.submit_video(SimpleNamespace(avatar='ava',voice='en-US-JennyNeural',expression='natural',text='Hello world')) == 'talk-test'


@pytest.mark.asyncio
@pytest.mark.parametrize('url',['http://example.com/file','https://evil.example/file','https://amazonaws.com.evil.example/file','https://user:pass@cloudfront.net/file','https://cloudfront.net:8443/file'])
async def test_reject_untrusted_downloads(url, tmp_path):
    with pytest.raises(ValueError, match='untrusted'): await providers.download_video(url, tmp_path/'video.mp4')


@pytest.mark.asyncio
async def test_only_reads_are_retried(monkeypatch):
    attempts = []
    async def sleep(seconds): pass
    monkeypatch.setattr(providers.asyncio, 'sleep', sleep)
    def respond(request):
        attempts.append(request.method)
        return httpx.Response(503 if len(attempts)<3 else 200)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert (await providers.request(client,'GET','https://api.d-id.com/talks/test')).status_code == 200
        assert len(attempts) == 3
        attempts.clear()
        with pytest.raises(httpx.HTTPStatusError): await providers.request(client,'POST','https://api.d-id.com/talks',json={})
        assert len(attempts) == 1
