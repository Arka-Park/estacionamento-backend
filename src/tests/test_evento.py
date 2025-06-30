from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy.orm import Session
from src.models import evento as models_evento
from src.models import estacionamento as models_estacionamento
from src.models.usuario import UsuarioDB
from src.auth.dependencies import get_current_user
from zoneinfo import ZoneInfo

brazil_timezone = ZoneInfo('America/Sao_Paulo')

def create_test_estacionamento(client, auth_headers, estacionamento_data):
    response = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]

def test_criar_evento(client, auth_headers):
    estacionamento_id = create_test_estacionamento(client, auth_headers, {
        "nome": "Estacionamento Teste Evento",
        "total_vagas": 100, "valor_primeira_hora": 10.0, "valor_demais_horas": 5.0, "valor_diaria": 50.0
    })
    
    now_local = datetime.now(brazil_timezone)
    response = client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Festival de Verão",
            "data_hora_inicio": (now_local - timedelta(hours=1)).isoformat(),
            "data_hora_fim": (now_local + timedelta(hours=1)).isoformat(),
            "valor_acesso_unico": 75.50,
            "id_estacionamento": estacionamento_id
        },
    )
    assert response.status_code == 201, f"Erro: {response.json()}"
    data = response.json()
    assert data["nome"] == "Festival de Verão"
    assert data["valor_acesso_unico"] == 75.50
    assert data["id_estacionamento"] == estacionamento_id
    assert "data_hora_inicio" in data
    assert "data_hora_fim" in data

def test_obter_evento(client, auth_headers):
    estacionamento_id = create_test_estacionamento(client, auth_headers, {
        "nome": "Estacionamento Obter Evento",
        "total_vagas": 100, "valor_primeira_hora": 10.0, "valor_demais_horas": 5.0, "valor_diaria": 50.0
    })

    now_local = datetime.now(brazil_timezone)
    res_create = client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Evento Obter",
            "data_hora_inicio": (now_local - timedelta(minutes=30)).isoformat(),
            "data_hora_fim": (now_local + timedelta(minutes=30)).isoformat(),
            "valor_acesso_unico": 10.0,
            "id_estacionamento": estacionamento_id
        },
    )
    assert res_create.status_code == 201
    evento_id = res_create.json()["id"]

    response = client.get(f"/api/eventos/{evento_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == evento_id
    assert data["nome"] == "Evento Obter"

def test_atualizar_evento(client, auth_headers):
    estacionamento_id = create_test_estacionamento(client, auth_headers, {
        "nome": "Estacionamento Atualizar Evento",
        "total_vagas": 100, "valor_primeira_hora": 10.0, "valor_demais_horas": 5.0, "valor_diaria": 50.0
    })

    now_local = datetime.now(brazil_timezone)
    res_create = client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Evento para Editar",
            "data_hora_inicio": (now_local - timedelta(hours=2)).isoformat(),
            "data_hora_fim": (now_local - timedelta(hours=1)).isoformat(),
            "valor_acesso_unico": 20.0,
            "id_estacionamento": estacionamento_id
        },
    )
    assert res_create.status_code == 201
    evento_id = res_create.json()["id"]

    updated_data = {
        "nome": "Evento Editado",
        "valor_acesso_unico": 25.0,
        "data_hora_inicio": (now_local - timedelta(hours=3)).isoformat(),
    }
    response = client.put(
        f"/api/eventos/{evento_id}", headers=auth_headers, json=updated_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Evento Editado"
    assert data["valor_acesso_unico"] == 25.0
    
    # Converta ambos os datetimes para UTC para uma comparação robusta
    # now_local é um datetime.datetime com tzinfo=brazil_timezone
    # datetime.fromisoformat(data["data_hora_inicio"]) pode ser naive se Pydantic não adicionar tzinfo na serialização
    # então, re-adicione tzinfo e converta para UTC para comparação
    
    # O valor esperado no fuso horário local
    expected_local_dt = now_local - timedelta(hours=3)

    # O valor recebido da API, convertido para um datetime aware (assumindo que a string ISO representa BRT)
    # Se a string ISO já incluir tzinfo, fromisoformat já criará um aware datetime
    # Se for naive, adicionamos o tzinfo do Brasil para que possamos converter para UTC
    received_from_api_dt = datetime.fromisoformat(data["data_hora_inicio"])
    if received_from_api_dt.tzinfo is None:
        received_from_api_dt = received_from_api_dt.replace(tzinfo=brazil_timezone)

    # Compare os valores em UTC para garantir que o ponto no tempo é o mesmo
    assert received_from_api_dt.astimezone(timezone.utc) == expected_local_dt.astimezone(timezone.utc)


def test_deletar_evento(client, auth_headers):
    estacionamento_id = create_test_estacionamento(client, auth_headers, {
        "nome": "Estacionamento Deletar Evento",
        "total_vagas": 100, "valor_primeira_hora": 10.0, "valor_demais_horas": 5.0, "valor_diaria": 50.0
    })

    now_local = datetime.now(brazil_timezone)
    res_create = client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Evento a ser Deletado",
            "data_hora_inicio": (now_local - timedelta(hours=1)).isoformat(),
            "data_hora_fim": (now_local + timedelta(hours=1)).isoformat(),
            "valor_acesso_unico": 15.0,
            "id_estacionamento": estacionamento_id
        },
    )
    assert res_create.status_code == 201
    evento_id = res_create.json()["id"]

    response = client.delete(f"/api/eventos/{evento_id}", headers=auth_headers)
    assert response.status_code == 204

    response_get = client.get(f"/api/eventos/{evento_id}", headers=auth_headers)
    assert response_get.status_code == 404

def test_listar_eventos_por_estacionamento(client, auth_headers):
    estacionamento_id = create_test_estacionamento(client, auth_headers, {
        "nome": "Estacionamento Listar Eventos",
        "total_vagas": 100, "valor_primeira_hora": 10.0, "valor_demais_horas": 5.0, "valor_diaria": 50.0
    })
    
    now_local = datetime.now(brazil_timezone)
    client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Evento Lista 1",
            "data_hora_inicio": (now_local - timedelta(hours=1)).isoformat(),
            "data_hora_fim": (now_local + timedelta(hours=1)).isoformat(),
            "valor_acesso_unico": 10.0,
            "id_estacionamento": estacionamento_id
        },
    )
    client.post(
        "/api/eventos/",
        headers=auth_headers,
        json={
            "nome": "Evento Lista 2",
            "data_hora_inicio": (now_local - timedelta(hours=2)).isoformat(),
            "data_hora_fim": (now_local + timedelta(hours=2)).isoformat(),
            "valor_acesso_unico": 20.0,
            "id_estacionamento": estacionamento_id
        },
    )
    
    response = client.get(f"/api/eventos/estacionamento/{estacionamento_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(e["nome"] == "Evento Lista 1" for e in data)
    assert any(e["nome"] == "Evento Lista 2" for e in data)