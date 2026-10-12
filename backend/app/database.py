"""SQLAlchemy ORM + SQLite persistence. SQLModel is a thin layer on this same ORM."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from .config import settings


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    prompt: Mapped[str] = mapped_column(Text)
    reference_id: Mapped[str] = mapped_column(String(36))
    headshot_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default='pending', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    thumbnails: Mapped[list['Thumbnail']] = relationship(back_populates='job', cascade='all, delete-orphan')


class Thumbnail(Base):
    __tablename__ = 'thumbnails'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    style_name: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(24), default='pending')
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    job: Mapped[Job] = relationship(back_populates='thumbnails')


is_sqlite = settings.database_url.startswith('sqlite:')
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout': 30} if is_sqlite else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

if is_sqlite:
    @event.listens_for(engine, 'connect')
    def configure_sqlite(conn, _):
        cur = conn.cursor()
        cur.execute('PRAGMA journal_mode=WAL')
        cur.execute('PRAGMA busy_timeout=30000')
        cur.execute('PRAGMA foreign_keys=ON')
        cur.close()


def create_tables():
    Base.metadata.create_all(engine)
