from fastapi import status

def test_criar_estacionamento(client, auth_headers):
    estacionamento_data = {
        "nome": "Estacionamento Teste",
        "endereco": "Rua Teste, 123",
        "total_vagas": 50,
        "valor_primeira_hora": 10.0,
        "valor_demais_horas": 5.0,
        "valor_diaria": 40.0
    }
    response = client.post("/api/estacionamentos/", json=estacionamento_data, headers=auth_headers) # <--- USAR auth_headers
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["nome"] == estacionamento_data["nome"]
    assert data["total_vagas"] == estacionamento_data["total_vagas"]

def test_listar_estacionamentos(client, auth_headers):
    estacionamento_data_1 = {
        "nome": "Estacionamento Teste 1",
        "total_vagas": 10
    }
    estacionamento_data_2 = {
        "nome": "Estacionamento Teste 2",
        "total_vagas": 20
    }
    client.post("/api/estacionamentos/", json=estacionamento_data_1, headers=auth_headers)
    client.post("/api/estacionamentos/", json=estacionamento_data_2, headers=auth_headers)

    response = client.get("/api/estacionamentos/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

def test_listar_estacionamentos_sem_autenticacao(client):
    response = client.get("/api/estacionamentos/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
