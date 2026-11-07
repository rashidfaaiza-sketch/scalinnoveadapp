from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: str = 'development'
    admin_password: str
    encryption_key: str = ''
    encryption_seed: str = ''
    static_dir: Path | None = None
    ephemeral_storage: bool = False
    database_url: str = 'sqlite+aiosqlite:///./data/studio.db'
    data_dir: Path = Path('./data')
    frontend_origin: str = Field(default='http://localhost:5173', validation_alias=AliasChoices('FRONTEND_ORIGIN', 'RENDER_EXTERNAL_URL', 'frontend_origin'))
    demo_mode: bool = False
    generation_mode: Literal['local', 'provider'] = 'local'
    local_tts_engine: Literal['espeak', 'loudkit'] = 'espeak'
    loudkit_model: str = 'loudreader/loudr-1'
    loudkit_revision: str = 'v0.1.1'
    openai_api_key: str = Field(default='', validation_alias=AliasChoices('STUDIO_OPENAI_API_KEY', 'OPENAI_API_KEY', 'openai_api_key'))
    did_api_key: str = ''
    openai_model: str = 'gpt-4o-mini'
    media_hosts: str = 'd-id.com,amazonaws.com,cloudfront.net'
    session_hours: int = 12
    max_video_bytes: int = 100_000_000

    @model_validator(mode='after')
    def resolve_generated_secret(self):
        if not self.encryption_key and self.encryption_seed:
            if len(self.encryption_seed) < 32:
                raise ValueError('ENCRYPTION_SEED must contain at least 32 characters')
            import base64
            import hashlib
            self.encryption_key = base64.urlsafe_b64encode(hashlib.sha256(self.encryption_seed.encode()).digest()).decode()
        return self

    def validate_runtime(self):
        if len(self.admin_password) < 12:
            raise ValueError('ADMIN_PASSWORD must contain at least 12 characters')
        if self.app_env == 'production' and (self.demo_mode or self.admin_password == 'change-this-local-password'):
            raise ValueError('Production requires DEMO_MODE=false and a unique ADMIN_PASSWORD')
        if self.app_env == 'production' and not self.frontend_origin.startswith('https://'):
            raise ValueError('Production requires an HTTPS FRONTEND_ORIGIN')
        from cryptography.fernet import Fernet
        Fernet(self.encryption_key.encode())
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
