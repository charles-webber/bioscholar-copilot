from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.db.session import engine
from app.main import app

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_OWNER_ID = UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def db() -> Iterator[Session]:
    database_name = engine.url.database or ""
    if not database_name.endswith("_test"):
        pytest.fail(
            "测试拒绝连接非测试库；请把 DATABASE_URL 指向名称以 _test 结尾的数据库"
        )

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_id] = lambda: OWNER_ID
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user_id, None)