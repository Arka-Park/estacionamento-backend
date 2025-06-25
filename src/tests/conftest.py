# pylint: disable=redefined-outer-name,too-many-arguments,unused-import

import os
import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from _pytest.monkeypatch import MonkeyPatch
from src.main import app
from src.database import get_db
from src.models.base import Base
from src.models.usuario import UsuarioDB, PessoaDB
from src.security import get_password_hash


os.environ["TESTING"] = "True"
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database_environment(monkeypatch_session):
    monkeypatch_session.setattr("src.database.engine", test_engine)
    monkeypatch_session.setattr("src.database.SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(name="db_session", scope="function")
def db_session_fixture():
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(name="client", scope="function")
def test_client_fixture(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def monkeypatch_session():
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(name="test_admin_user", scope="function")
def create_test_admin_user(db_session):
    admin_password = "admin_test_pass"
    hashed_password = get_password_hash(admin_password)
    pessoa = PessoaDB(nome="Admin Test", cpf="00000000000", email="admin_test@example.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)
    admin_user = UsuarioDB(id_pessoa=pessoa.id, login="admin_test", senha=hashed_password, role="admin", admin_id=None)
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)
    return admin_user, admin_password

@pytest.fixture(name="test_employee_user", scope="function")
def create_test_employee_user(db_session, test_admin_user):
    admin_obj, _ = test_admin_user
    employee_password = "emp_test_pass"
    hashed_password = get_password_hash(employee_password)
    pessoa = PessoaDB(nome="Employee Test", cpf="11111111111", email="employee_test@example.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)
    employee_user = UsuarioDB(id_pessoa=pessoa.id, login="employee_test", senha=hashed_password, role="funcionario", admin_id=admin_obj.id)
    db_session.add(employee_user)
    db_session.commit()
    db_session.refresh(employee_user)
    return employee_user, employee_password

@pytest.fixture(name="auth_headers", scope="function")
def get_auth_headers(client, test_admin_user):
    admin_obj, admin_password = test_admin_user
    response = client.post(
        "/api/token",
        data={"username": admin_obj.login, "password": admin_password}
    )
    token_data = response.json()
    if "access_token" not in token_data:
        pytest.fail(f"Token data does not contain 'access_token': {token_data}")
    access_token = token_data['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers

@pytest.fixture(name="auth_headers_employee", scope="function")
def get_auth_headers_employee(client, test_employee_user):
    employee_obj, employee_password = test_employee_user
    response = client.post(
        "/api/token",
        data={"username": employee_obj.login, "password": employee_password}
    )
    token_data = response.json()
    if "access_token" not in token_data:
        pytest.fail(f"Token data does not contain 'access_token': {token_data}")
    access_token = token_data['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers
