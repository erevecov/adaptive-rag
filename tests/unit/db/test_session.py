from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

from adaptive_rag.db.base import Base
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_base_is_declarative_base_subclass():
    assert issubclass(Base, DeclarativeBase)
    # La metadata compartida permite que los modelos se registren al importarse.
    assert hasattr(Base, "metadata")


def test_sqlite_engine_can_execute_query():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        value = session.execute(text("select 1")).scalar_one()

    assert value == 1
