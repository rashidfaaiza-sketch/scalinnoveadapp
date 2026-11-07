from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class TextIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ProjectIn(TextIn):
    name: str = Field(min_length=1, max_length=160)
    product: str = Field(min_length=1, max_length=200)
    audience: str = Field(min_length=1, max_length=1000)
    objective: str = Field(min_length=1, max_length=1000)


class ScriptIn(TextIn):
    hook: str = Field(min_length=1, max_length=1000)
    body: str = Field(min_length=1, max_length=5000)
    cta: str = Field(min_length=1, max_length=1000)
    platform: Literal['Short-form', 'YouTube'] = 'Short-form'


class GenerateIn(BaseModel):
    platform: Literal['Short-form', 'YouTube'] = 'Short-form'
    tone: Literal['Confident', 'Friendly', 'Bold', 'Educational'] = 'Confident'


class RenderIn(TextIn):
    script_id: str
    avatar: Literal['ava', 'noah', 'mia'] = 'ava'
    voice: Literal['en-US-JennyNeural', 'en-US-GuyNeural', 'en-GB-SoniaNeural', 'local-neutral', 'local-warm', 'local-bright'] = 'en-US-JennyNeural'
    ratio: Literal['9:16', '1:1', '16:9'] = '9:16'
    expression: Literal['natural', 'lively', 'serious'] = 'natural'
    name: str = Field(min_length=1, max_length=160)


class RenameIn(TextIn):
    name: str = Field(min_length=1, max_length=160)


class KeyIn(BaseModel):
    key: str = Field(min_length=5, max_length=1000)


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=500)


def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in {'encrypted', 'token_hash', 'text', 'provider_id'}}


class ExportIn(BaseModel):
    ratio: Literal['9:16', '1:1', '16:9']
