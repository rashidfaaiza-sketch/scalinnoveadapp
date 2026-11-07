import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .config import settings


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    product: Mapped[str] = mapped_column(String(200))
    audience: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Script(Base):
    __tablename__ = 'scripts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    hook: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    cta: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String, default=now)


class Video(Base):
    __tablename__ = 'videos'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id'), index=True)
    script_id: Mapped[str] = mapped_column(ForeignKey('scripts.id'))
    name: Mapped[str] = mapped_column(String(160))
    text: Mapped[str] = mapped_column(Text)
    avatar: Mapped[str] = mapped_column(String(40))
    voice: Mapped[str] = mapped_column(String(80))
    ratio: Mapped[str] = mapped_column(String(10))
    expression: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    provider_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(100), nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean)
    engine: Mapped[str] = mapped_column(String(20), default='provider', server_default='provider')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class Credential(Base):
    __tablename__ = 'credentials'
    provider: Mapped[str] = mapped_column(String(30), primary_key=True)
    encrypted: Mapped[str] = mapped_column(Text)


class Session(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[float]


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
DB = async_sessionmaker(engine, expire_on_commit=False)
