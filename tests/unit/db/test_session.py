from sqlalchemy import text

from adaptive_rag.db.base import Base
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_base_metadata_starts_empty():
    assert Base.metadata.tables == {}


def test_sqlite_engine_can_execute_query():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        value = session.execute(text("select 1")).scalar_one()

    assert value == 1
