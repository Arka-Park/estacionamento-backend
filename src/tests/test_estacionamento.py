import pytest
from src import security
from src.models.usuario import PessoaDB, UsuarioDB


@pytest.fixture(scope="function")
def admin_estacionamento_token(db_session):
    """
    Cria um usuário admin de teste e retorna um token de acesso para ele.
    """
    pessoa = PessoaDB(nome="Admin Estacionamento", cpf="55544433322", email="estacionamento@test.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)

    hashed_password = security.get_password_hash("estacionamento123")
    admin_user = UsuarioDB(
        id_pessoa=pessoa.id,
        login="admin_estacionamento",
        senha=hashed_password,
        role="admin"
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)
    token = security.create_access_token(data={"sub": admin_user.login, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


def test_criar_estacionamento(client, db_session, admin_estacionamento_token):
    """
    Testa se um admin autenticado consegue criar um novo estacionamento.
    """
    response = client.post(
        "/api/estacionamentos/",
        headers=admin_estacionamento_token,  # 1. Envia o token de autenticação
        json={"nome": "Estacionamento Teste Pytest", "total_vagas": 75}
    )
    assert response.status_code == 201, f"Erro: {response.json()}"
    data = response.json()
    assert data["nome"] == "Estacionamento Teste Pytest"


def test_listar_estacionamentos(client, db_session, admin_estacionamento_token):
    """
    Testa se um admin autenticado consegue listar os estacionamentos.
    """
    client.post(
        "/api/estacionamentos/",
        headers=admin_estacionamento_token,
        json={"nome": "Shopping A", "total_vagas": 150}
    )
    response = client.get("/api/estacionamentos/", headers=admin_estacionamento_token)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["nome"] == "Shopping A"


def test_nao_deve_criar_estacionamento_sem_token(client, db_session):
    """
    Testa se a rota retorna 401 Unauthorized ao tentar criar sem um token.
    """
    response = client.post(
        "/api/estacionamentos/",
        json={"nome": "Estacionamento Fantasma", "total_vagas": 10}
    )
    assert response.status_code == 401