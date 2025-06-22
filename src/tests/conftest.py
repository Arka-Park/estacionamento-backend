import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import get_db
from src.models.base import Base # Importa a Base central

# --- Configuração do banco de dados de teste em memória (SQLite) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas no banco de teste uma única vez para toda a sessão de testes
Base.metadata.create_all(bind=engine)

# Sobrescreve a dependência get_db para usar o banco de teste
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Cria um cliente de teste que será usado em todos os testes
@pytest.fixture(scope="module")
def client():
    return TestClient(app)

# --- A Fixture Compartilhada ---
@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que fornece uma sessão de banco de dados limpa para cada teste.
    """
    # Limpa as tabelas antes de cada teste
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()