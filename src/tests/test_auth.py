import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.database import get_db
from src.models.estacionamento import Base
from src.models.usuario import PessoaDB, UsuarioDB
from src import security

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """Fixture que limpa as tabelas e cria um usuário de teste."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    pessoa_teste = PessoaDB(nome="Admin Teste", cpf="12345678901", email="admin@teste.com")
    db.add(pessoa_teste)
    db.commit()
    db.refresh(pessoa_teste)

    # Senha em texto plano: 'admin123'
    hashed_password = security.get_password_hash("admin123")
    usuario_teste = UsuarioDB(
        id_pessoa=pessoa_teste.id,
        login="admin_teste",
        senha=hashed_password,
        role="admin"
    )
    db.add(usuario_teste)
    db.commit()
    
    yield db # O teste é executado aqui
    
    db.close()

def test_login_com_sucesso(db_session):
    """
    Testa se o endpoint /api/token retorna um token de acesso com credenciais válidas.
    """
    response = client.post(
        "/api/token",  
        data={"username": "admin_teste", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_com_senha_errada(db_session):
    """
    Testa se o endpoint /api/token retorna erro 401 com senha incorreta.
    """
    response = client.post(
        "/api/token", 
        data={"username": "admin_teste", "password": "senhaerrada"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Login ou senha incorretos"
    
def test_login_com_usuario_inexistente(db_session):
    """
    Testa se o endpoint /api/token retorna erro 401 com um usuário que não existe.
    """
    response = client.post(
        "/api/token",
        data={"username": "usuario_fantasma", "password": "123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Login ou senha incorretos"