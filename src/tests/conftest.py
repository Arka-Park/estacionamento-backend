import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.database import get_db, engine as app_main_engine, SessionLocal as AppSessionLocal 
from src.models.base import Base
from src.models.usuario import UsuarioDB, PessoaDB
from src.security import get_password_hash, create_access_token
from _pytest.monkeypatch import MonkeyPatch

# Configuração para o banco de dados de teste em memória (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Fixture monkeypatch de escopo de sessão
@pytest.fixture(scope="session")
def session_monkeypatch(request):
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()

# Fixture para sobrescrever o banco de dados principal da aplicação durante os testes
@pytest.fixture(scope="session")
def override_app_db_connection(session_monkeypatch):
    session_monkeypatch.setattr("src.database.engine", test_engine)
    session_monkeypatch.setattr("src.database.SessionLocal", TestingSessionLocal)
    yield

# Esta fixture fornece uma sessão de banco de dados com transação para cada FUNÇÃO de teste.
@pytest.fixture(name="db_session", scope="function") 
def override_get_db_fixture():
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    
    # Cria todas as tabelas ANTES de cada teste
    Base.metadata.create_all(bind=test_engine) 

    try:
        yield db 
    finally:
        db.close() 
        transaction.rollback() # Reverte todas as alterações feitas no teste
        connection.close() 
        # Garante que o banco está limpo para o próximo teste de função
        Base.metadata.drop_all(bind=test_engine) 


# Esta fixture fornece o cliente de teste para fazer requisições à API.
# MUDOU PARA scope="function" para garantir que use a mesma db_session do teste.
@pytest.fixture(name="client", scope="function") # <--- MUDANÇA CRUCIAL AQUI
def test_client_fixture(override_app_db_connection, db_session): # Agora depende da db_session (function-scoped)
    """
    Cliente de teste FastAPI para fazer requisições HTTP nos testes.
    """
    # Define uma nova função geradora que será a sobrescrita para get_db.
    # Esta função geradora VAI YIELD A INSTÂNCIA ESPECÍFICA de db_session para o teste atual.
    def _override_get_db():
        yield db_session # Yields a referência à sessão db_session para o FastAPI

    app.dependency_overrides[get_db] = _override_get_db 
    
    with TestClient(app) as c:
        yield c 
    app.dependency_overrides.clear()


# --- FIXTURES PARA USUÁRIOS E AUTENTICAÇÃO (Permanecem scope="function") ---

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
    # Verifica se a chave 'access_token' existe antes de acessá-la
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
    # Verifica se a chave 'access_token' existe antes de acessá-la
    if "access_token" not in token_data:
        pytest.fail(f"Token data does not contain 'access_token': {token_data}")
    access_token = token_data['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers