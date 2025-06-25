def test_login_com_sucesso(client, test_admin_user):
    """
    Testa se o endpoint /api/token retorna um token de acesso com credenciais válidas.
    """
    admin_user_obj, admin_password = test_admin_user

    response = client.post(
        "/api/token",
        data={"username": admin_user_obj.login, "password": admin_password}
    )
    assert response.status_code == 200, f"Erro: {response.json()}"
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_login_com_senha_errada(client):
    """
    Testa se o endpoint /api/token retorna 401 com senha inválida.
    """
    response = client.post(
        "/api/token",
        data={"username": "admin_test", "password": "senha_errada"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Login ou senha incorretos"}

def test_login_com_usuario_inexistente(client):
    """
    Testa se o endpoint /api/token retorna 401 com usuário inexistente.
    """
    response = client.post(
        "/api/token",
        data={"username": "usuario_nao_existe", "password": "qualquersenha"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Login ou senha incorretos"}
