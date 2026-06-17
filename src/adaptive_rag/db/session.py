from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.config.settings import get_settings


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = create_engine_from_url(get_settings().database_url)
SessionLocal = create_session_factory(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
