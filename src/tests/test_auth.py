import pytest
from src.models.usuario import PessoaDB, UsuarioDB
from src import security    

@pytest.fixture(scope="function")
def setup_auth_data(db_session):
    """Cria uma pessoa e um usuário administrador para os testes de auth."""
    pessoa = PessoaDB(nome="Admin Auth Test", cpf="12345678901", email="admin.auth@test.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)

    hashed_password = security.get_password_hash("admin123")
    usuario = UsuarioDB(
        id_pessoa=pessoa.id,
        login="admin_auth_test",
        senha=hashed_password,
        role="admin"
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario

def test_login_com_sucesso(client, setup_auth_data):
    """
    Testa se o endpoint /api/token retorna um token de acesso com credenciais válidas.
    """
    response = client.post(
        "/api/token",
        data={"username": "admin_auth_test", "password": "admin123"}
    )
    assert response.status_code == 200, f"Erro: {response.json()}"
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_com_senha_errada(client, setup_auth_data):
    """
    Testa se o endpoint /api/token retorna erro 401 com senha incorreta.
    """
    response = client.post(
        "/api/token", 
        data={"username": "admin_auth_test", "password": "senhaerrada"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Login ou senha incorretos"
    
def test_login_com_usuario_inexistente(client, db_session):
    """
    Testa se o endpoint /api/token retorna erro 401 com um usuário que não existe.
    """
    response = client.post(
        "/api/token",
        data={"username": "usuario_fantasma", "password": "123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Login ou senha incorretos"