# pylint: disable=redefined-outer-name,too-many-arguments

import pytest
from sqlalchemy.exc import ProgrammingError
from src import security
from src.models.estacionamento import EstacionamentoDB
from src.models.usuario import PessoaDB, UsuarioDB

@pytest.fixture(scope="function")
def setup_evento_data(db_session):
    for table in reversed(UsuarioDB.metadata.sorted_tables):
        try:
            db_session.execute(table.delete())
        except ProgrammingError:
            pass
    db_session.commit()

    estacionamento = EstacionamentoDB(nome="Shopping Teste Evento", total_vagas=300)
    db_session.add(estacionamento)
    db_session.commit()
    db_session.refresh(estacionamento)

    pessoa = PessoaDB(nome="Admin Evento", cpf="98765432100", email="evento@test.com")
    db_session.add(pessoa)
    db_session.commit()
    db_session.refresh(pessoa)

    hashed_password = security.get_password_hash("evento123")
    admin_user = UsuarioDB(
        id_pessoa=pessoa.id,
        login="admin_evento",
        senha=hashed_password,
        role="admin"
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    return {"estacionamento_id": estacionamento.id, "admin_user": admin_user}


@pytest.fixture(scope="function")
def admin_evento_token(setup_evento_data):
    user = setup_evento_data["admin_user"]
    token = security.create_access_token(data={"sub": user.login, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_criar_evento(client, setup_evento_data, admin_evento_token):
    response = client.post(
        "/api/eventos/",
        headers=admin_evento_token,
        json={
            "nome": "Festival de Verão",
            "data_evento": "2025-01-20",
            "hora_inicio": "18:00:00",
            "hora_fim": "23:00:00",
            "valor_acesso_unico": 75.50,
            "id_estacionamento": setup_evento_data["estacionamento_id"]
        },
    )
    assert response.status_code == 201, f"Erro: {response.json()}"
    data = response.json()
    assert data["nome"] == "Festival de Verão"
    assert data["hora_inicio"] == "18:00:00"


def test_atualizar_evento(client, setup_evento_data, admin_evento_token):
    res_create = client.post(
        "/api/eventos/",
        headers=admin_evento_token,
        json={
            "nome": "Evento para Editar",
            "data_evento": "2025-05-10",
            "hora_inicio": "10:00:00",
            "hora_fim": "12:00:00",
            "valor_acesso_unico": 20.0,
            "id_estacionamento": setup_evento_data["estacionamento_id"]
        },
    )
    evento_id = res_create.json()["id"]

    response = client.put(
        f"/api/eventos/{evento_id}",
        headers=admin_evento_token,
        json={"nome": "Evento Editado com Sucesso"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Evento Editado com Sucesso"
    assert data["valor_acesso_unico"] == 20.0


def test_deletar_evento(client, setup_evento_data, admin_evento_token):
    res_create = client.post(
        "/api/eventos/",
        headers=admin_evento_token,
        json={
            "nome": "Evento a ser Deletado",
            "data_evento": "2025-06-15",
            "hora_inicio": "09:00:00",
            "hora_fim": "17:00:00",
            "valor_acesso_unico": 15.0,
            "id_estacionamento": setup_evento_data["estacionamento_id"]
        },
    )
    evento_id = res_create.json()["id"]

    response_delete = client.delete(f"/api/eventos/{evento_id}", headers=admin_evento_token)
    assert response_delete.status_code == 204

    response_get = client.get(f"/api/eventos/{evento_id}", headers=admin_evento_token)
    assert response_get.status_code == 404
