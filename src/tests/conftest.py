# src/tests/conftest.py
import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.database import get_db, engine as app_main_engine, SessionLocal as AppSessionLocal # Importar o engine e SessionLocal reais
from src.models.base import Base
from src.models.usuario import UsuarioDB, PessoaDB
from src.security import get_password_hash, create_access_token
from _pytest.monkeypatch import MonkeyPatch # NOVO: Importar MonkeyPatch explicitamente

# Configuração para o banco de dados de teste em memória (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# NOVO: Fixture monkeypatch de escopo de sessão
@pytest.fixture(scope="session")
def session_monkeypatch(request):
    """
    Uma versão da fixture monkeypatch com escopo de sessão.
    Isso permite que fixtures de sessão usem monkeypatch.
    """
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo() # Garante que as alterações sejam desfeitas após a sessão

# Fixture para sobrescrever o banco de dados principal da aplicação durante os testes
@pytest.fixture(scope="session")
def override_app_db_connection(session_monkeypatch): # Agora depende do nosso monkeypatch de sessão
    """
    Substitui temporariamente o engine e o SessionLocal da aplicação principal
    pelos do banco de dados SQLite de teste.
    """
    session_monkeypatch.setattr("src.database.engine", test_engine)
    session_monkeypatch.setattr("src.database.SessionLocal", TestingSessionLocal)
    yield

# Esta fixture fornece uma sessão de banco de dados limpa para CADA TESTE.
@pytest.fixture(name="db_session", scope="function")
def override_get_db_fixture():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

# Esta fixture fornece o cliente de teste para fazer requisições à API.
@pytest.fixture(name="client", scope="module")
def test_client_fixture(override_app_db_connection): # Adiciona dependência na fixture de patching
    """
    Cliente de teste FastAPI para fazer requisições HTTP nos testes.
    """
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- NOVAS FIXTURES PARA TESTES DE USUÁRIO (Criadas anteriormente) ---
# (Certifique-se de que este conteúdo está AQUI, abaixo das fixtures principais.)

@pytest.fixture(name="test_admin_user", scope="function")
def create_test_admin_user(db_session):
    admin_password = "admin_test_pass"
    hashed_password = get_password_hash(admin_password)
    pessoa = PessoaDB(nome="Admin Test", cpf="000.000.000-00", email="admin_test@example.com")
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
    pessoa = PessoaDB(nome="Employee Test", cpf="111.111.111-11", email="employee_test@example.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)
    employee_user = UsuarioDB(id_pessoa=pessoa.id, login="employee_test", senha=hashed_password, role="funcionario", admin_id=admin_obj.id)
    db_session.add(employee_user)
    db_session.commit()
    db_session.refresh(employee_user)
    return employee_user, employee_password

@pytest.fixture(name="auth_headers", scope="function")
def get_auth_headers(test_admin_user):
    admin_obj, _ = test_admin_user
    token_data = {"sub": admin_obj.login, "role": admin_obj.role}
    access_token = create_access_token(token_data)
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers

@pytest.fixture(name="auth_headers_employee", scope="function")
def get_auth_headers_employee(test_employee_user):
    employee_obj, _ = test_employee_user
    token_data = {"sub": employee_obj.login, "role": employee_obj.role}
    access_token = create_access_token(token_data)
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers