import json
from datetime import datetime, timedelta, timezone, date, time
from zoneinfo import ZoneInfo
from fastapi import status
from sqlalchemy.orm import Session
from src.models import acesso as models_acesso
from src.models import estacionamento as models_estacionamento
from src.models import evento as models_evento
from src.models import faturamento as models_faturamento


brazil_timezone = ZoneInfo('America/Sao_Paulo')


def test_register_entry(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Teste",
        "total_vagas": 100,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "ABC1234",
        "id_estacionamento": estacionamento_id
    }
    response = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["placa"] == "ABC1234"
    assert "hora_entrada" in data
    assert data["hora_saida"] is None
    assert data["tipo_acesso"] == "hora"
    assert data["id_evento"] is None


def test_register_entry_event_access(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Evento",
        "total_vagas": 200,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    now_local = datetime.now(brazil_timezone)
    event_data = {
        "nome": "Show Rock Teste",
        "data_hora_inicio": (now_local - timedelta(hours=1)).isoformat(),
        "data_hora_fim": (now_local + timedelta(hours=1)).isoformat(),
        "valor_acesso_unico": 30.0,
        "id_estacionamento": estacionamento_id
    }
    response_evento = client.post("/api/eventos/", json=event_data, headers=auth_headers)
    assert response_evento.status_code == status.HTTP_201_CREATED
    event_id = response_evento.json()["id"]

    entry_data = {
        "placa": "EVENTO1",
        "id_estacionamento": estacionamento_id
    }
    response = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["placa"] == "EVENTO1"
    assert data["tipo_acesso"] == "evento"
    assert data["id_evento"] == event_id


def test_register_entry_estacionamento_not_found(client, auth_headers):
    entry_data = {
        "placa": "ABC1234",
        "id_estacionamento": 999
    }
    response = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Estacionamento não encontrado" in response.json()["detail"]


def test_register_entry_estacionamento_full(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Cheio",
        "total_vagas": 1,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "ABC1234",
        "id_estacionamento": estacionamento_id
    }
    response = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED

    response_full = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response_full.status_code == status.HTTP_400_BAD_REQUEST
    assert "Estacionamento lotado" in response_full.json()["detail"]


def test_register_exit(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Saida",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "XYZ7890",
        "id_estacionamento": estacionamento_id
    }
    response_entry = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response_entry.status_code == status.HTTP_201_CREATED
    acesso_id = response_entry.json()["id"]

    response_exit = client.put(f"/api/acessos/{acesso_id}/saida", headers=auth_headers)
    assert response_exit.status_code == status.HTTP_200_OK
    data = response_exit.json()
    assert data["id"] == acesso_id
    assert "hora_saida" in data
    assert data["valor_total"] >= 0


def test_register_exit_not_found(client, auth_headers):
    response = client.put("/api/acessos/999/saida", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Acesso não encontrado" in response.json()["detail"]


def test_register_exit_already_exited(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Ja Saiu",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "EXITED1",
        "id_estacionamento": estacionamento_id
    }
    response_entry = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    acesso_id = response_entry.json()["id"]

    response_exit_first = client.put(f"/api/acessos/{acesso_id}/saida", headers=auth_headers)
    assert response_exit_first.status_code == status.HTTP_200_OK

    response_exit_second = client.put(f"/api/acessos/{acesso_id}/saida", headers=auth_headers)
    assert response_exit_second.status_code == status.HTTP_400_BAD_REQUEST
    assert "Saída já registrada para este acesso." in response_exit_second.json()["detail"]


def test_register_exit_hourly_calculation(client, auth_headers, mocker):
    estacionamento_data = {
        "nome": "Estacionamento Horas",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    estacionamento_id = response_estacionamento.json()["id"]

    fixed_hora_entrada = datetime(2025, 1, 1, 10, 0, 0, tzinfo=brazil_timezone) # Times in BRT
    fixed_hora_saida = datetime(2025, 1, 1, 12, 30, 0, tzinfo=brazil_timezone)   # Times in BRT
    fixed_hora_faturamento = datetime(2025, 1, 1, 12, 30, 0, tzinfo=brazil_timezone)

    mock_datetime_module = mocker.patch('src.routes.acesso.datetime', autospec=True)
    mock_datetime_module.now.side_effect = [fixed_hora_entrada, fixed_hora_saida, fixed_hora_faturamento]
    mock_datetime_module.timedelta = timedelta 

    entry_data = {
        "placa": "HORAS1",
        "id_estacionamento": estacionamento_id
    }
    response_entry = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response_entry.status_code == status.HTTP_201_CREATED
    acesso_id = response_entry.json()["id"]

    response_exit = client.put(f"/api/acessos/{acesso_id}/saida", headers=auth_headers)
    assert response_exit.status_code == status.HTTP_200_OK
    data = response_exit.json()
    
    expected_valor_total = 10.0 + 5.0 * 2
    assert data["valor_total"] == expected_valor_total


def test_register_exit_event_specific_value(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Evento Valor",
        "total_vagas": 50,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    now_local = datetime.now(brazil_timezone)
    event_data = {
        "nome": "Festa Junina",
        "data_hora_inicio": (now_local - timedelta(hours=1)).isoformat(),
        "data_hora_fim": (now_local + timedelta(hours=2)).isoformat(),
        "valor_acesso_unico": 25.0,
        "id_estacionamento": estacionamento_id
    }
    response_evento = client.post("/api/eventos/", json=event_data, headers=auth_headers)
    assert response_evento.status_code == status.HTTP_201_CREATED

    entry_data = {
        "placa": "EVENTO2",
        "id_estacionamento": estacionamento_id
    }
    response_entry = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response_entry.status_code == status.HTTP_201_CREATED
    acesso_id = response_entry.json()["id"]

    response_exit = client.put(f"/api/acessos/{acesso_id}/saida", headers=auth_headers)
    assert response_exit.status_code == status.HTTP_200_OK
    data = response_exit.json()
    assert data["valor_total"] == 25.0


def test_list_acessos(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Listagem",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "LIST1",
        "id_estacionamento": estacionamento_id
    }
    client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    client.post("/api/acessos/", json=entry_data, headers=auth_headers)

    response = client.get("/api/acessos/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 2


def test_get_acesso_by_id(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Get ID",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "GETID1",
        "id_estacionamento": estacionamento_id
    }
    response_entry = client.post("/api/acessos/", json=entry_data, headers=auth_headers)
    assert response_entry.status_code == status.HTTP_201_CREATED
    acesso_id = response_entry.json()["id"]

    response = client.get(f"/api/acessos/{acesso_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == acesso_id
    assert response.json()["placa"] == "GETID1"


def test_get_acesso_by_id_not_found(client, auth_headers):
    response = client.get("/api/acessos/999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Acesso não encontrado" in response.json()["detail"]


def test_register_entry_unauthorized(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento No Auth",
        "total_vagas": 10,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 50.0
    }
    response_estacionamento = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers)
    assert response_estacionamento.status_code == status.HTTP_201_CREATED
    estacionamento_id = response_estacionamento.json()["id"]

    entry_data = {
        "placa": "NOAUTH1",
        "id_estacionamento": estacionamento_id
    }
    response = client.post("/api/acessos/", json=entry_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]


def test_register_exit_unauthorized(client):
    response = client.put("/api/acessos/1/saida")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_acessos_unauthorized(client):
    response = client.get("/api/acessos/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_acesso_by_id_unauthorized(client):
    response = client.get("/api/acessos/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED