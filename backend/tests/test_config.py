from cryptography.fernet import Fernet
from app.config import Settings


def test_cloud_and_local_openai_key_names(monkeypatch):
    monkeypatch.delenv('STUDIO_OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    base = dict(_env_file=None, admin_password='test-password-long-enough', encryption_key=Fernet.generate_key().decode())
    assert Settings(**base, STUDIO_OPENAI_API_KEY='cloud-test-value').openai_api_key == 'cloud-test-value'
    assert Settings(**base, OPENAI_API_KEY='local-test-value').openai_api_key == 'local-test-value'
    monkeypatch.setenv('STUDIO_OPENAI_API_KEY', 'cloud-test-value')
    monkeypatch.setenv('OPENAI_API_KEY', 'local-test-value')
    assert Settings(**base).openai_api_key == 'cloud-test-value'


def test_render_generated_secret_and_public_origin(monkeypatch):
    monkeypatch.delenv('FRONTEND_ORIGIN', raising=False)
    monkeypatch.delenv('ENCRYPTION_KEY', raising=False)
    monkeypatch.setenv('RENDER_EXTERNAL_URL','https://forma-test.onrender.com')
    monkeypatch.setenv('ENCRYPTION_SEED','a-strong-test-seed-with-at-least-32-characters')
    config=Settings(_env_file=None, admin_password='unique-production-password', app_env='production', demo_mode=False)
    config.validate_runtime()
    assert config.frontend_origin=='https://forma-test.onrender.com'
    encrypted=Fernet(config.encryption_key.encode()).encrypt(b'test')
    assert Fernet(config.encryption_key.encode()).decrypt(encrypted)==b'test'
    assert Settings(_env_file=None,admin_password='unique-production-password').encryption_key==config.encryption_key


def test_existing_encryption_key_is_preserved():
    key=Fernet.generate_key().decode()
    config=Settings(_env_file=None,admin_password='test-password-long-enough',encryption_key=key,encryption_seed='different-seed-that-is-long-enough')
    assert config.encryption_key==key
