# src/tests/test_usuario.py
import pytest
from fastapi import status
from src.security import verify_password, get_password_hash
from src.models.usuario import UsuarioDB, PessoaDB

def test_admin_create_employee(client, db_session, auth_headers):
    """Admin deve conseguir criar um novo usuário funcionário."""
    new_employee_data = {
        "nome": "Novo Funcionario",
        "cpf": "222.222.222-22",
        "email": "novo.funcionario@example.com"
    }
    new_user_data = {
        "login": "novo_funcionario_login",
        "password": "senha_nova_func",
        "role": "funcionario"
    }
    
    # CORRIGIDO: Enviar dados aninhados sob as chaves esperadas pelo FastAPI
    request_body_for_creation = {
        "pessoa_data": new_employee_data,
        "user_data": new_user_data
    }

    response = client.post(
        "/api/usuarios/",
        json=request_body_for_creation, # Envia o dicionário aninhado
        headers=auth_headers
    )
    
    print(response.json()) # Manter para ver a resposta detalhada em caso de novos 422
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["login"] == new_user_data["login"]
    assert data["role"] == new_user_data["role"]
    assert "admin_id" in data
    assert data["admin_id"] == db_session.query(UsuarioDB).filter(UsuarioDB.login == "admin_test").first().id
    
    # Verifica no banco de dados
    db_new_user = db_session.query(UsuarioDB).filter(UsuarioDB.login == new_user_data["login"]).first()
    assert db_new_user is not None
    assert verify_password(new_user_data["password"], db_new_user.senha)
    assert db_new_user.admin_id == db_session.query(UsuarioDB).filter(UsuarioDB.login == "admin_test").first().id


def test_employee_cannot_create_user(client, auth_headers_employee):
    """Funcionário NÃO deve conseguir criar um novo usuário."""
    # CORRIGIDO: Enviar dados aninhados para este teste também
    new_employee_data_attempt = {"nome": "Func Tentativa", "cpf": "333.333.333-33", "email": "func.tentativa@example.com"}
    new_user_data_attempt = {"login": "func_tentativa_login", "password": "senha_func_tentativa", "role": "funcionario"}

    request_body_for_creation_attempt = {
        "pessoa_data": new_employee_data_attempt,
        "user_data": new_user_data_attempt
    }
    
    response = client.post(
        "/api/usuarios/",
        json=request_body_for_creation_attempt, # Envia o dicionário aninhado
        headers=auth_headers_employee
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN # Apenas admins podem criar


def test_admin_list_users(client, db_session, auth_headers, test_employee_user):
    """Admin deve listar a si mesmo e seus funcionários."""
    admin_obj, _ = db_session.query(UsuarioDB).filter(UsuarioDB.login == "admin_test").first(), "senha_dummy"
    employee_obj, _ = test_employee_user
    
    response = client.get("/api/usuarios/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    
    user_logins = {u["login"] for u in users}
    assert admin_obj.login in user_logins
    assert employee_obj.login in user_logins


def test_employee_list_self(client, db_session, auth_headers_employee, test_employee_user): # ADICIONADO: db_session
    """Funcionário deve listar apenas a si mesmo."""
    employee_obj, _ = test_employee_user
    
    response = client.get("/api/usuarios/", headers=auth_headers_employee)
    
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    
    assert len(users) == 1
    assert users[0]["login"] == employee_obj.login
    assert users[0]["role"] == employee_obj.role
    assert users[0]["admin_id"] == employee_obj.admin_id


def test_admin_get_employee(client, auth_headers, test_employee_user):
    """Admin deve conseguir obter um funcionário específico que ele gerencia."""
    employee_obj, _ = test_employee_user
    
    response = client.get(f"/api/usuarios/{employee_obj.id}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["login"] == employee_obj.login
    assert data["role"] == "funcionario"
    assert data["admin_id"] == employee_obj.admin_id

def test_admin_get_other_admin_forbidden(client, db_session, auth_headers):
    """Admin NÃO deve conseguir obter detalhes de outro admin (não criado por ele)."""
    admin2_password = "admin2_test_pass"
    hashed_password2 = get_password_hash(admin2_password)

    pessoa2 = PessoaDB(nome="Admin Test 2", cpf="000.000.000-02", email="admin2_test@example.com")
    db_session.add(pessoa2)
    db_session.commit()
    db_session.refresh(pessoa2)

    admin2_user = UsuarioDB(
        id_pessoa=pessoa2.id,
        login="admin_test2",
        senha=hashed_password2,
        role="admin",
        admin_id=None
    )
    db_session.add(admin2_user)
    db_session.commit()
    db_session.refresh(admin2_user)

    response = client.get(f"/api/usuarios/{admin2_user.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_employee_get_self(client, auth_headers_employee, test_employee_user):
    """Funcionário deve conseguir obter seus próprios detalhes."""
    employee_obj, _ = test_employee_user
    
    response = client.get(f"/api/usuarios/{employee_obj.id}", headers=auth_headers_employee)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["login"] == employee_obj.login

def test_employee_get_other_user_forbidden(client, auth_headers_employee, test_admin_user):
    """Funcionário NÃO deve conseguir obter detalhes de outro usuário (nem mesmo seu admin diretamente por ID)."""
    admin_obj, _ = test_admin_user
    
    response = client.get(f"/api/usuarios/{admin_obj.id}", headers=auth_headers_employee)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_update_employee(client, db_session, auth_headers, test_employee_user):
    """Admin deve conseguir atualizar dados de seu funcionário."""
    employee_obj, _ = test_employee_user
    updated_login = "updated_employee_login"
    
    update_request_body = {
        "login": updated_login,
        "password": "emp_test_pass",
        "role": "funcionario"
    }

    response = client.put(
        f"/api/usuarios/{employee_obj.id}",
        json=update_request_body,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["login"] == updated_login
    
    db_session.refresh(employee_obj)
    assert employee_obj.login == updated_login


def test_employee_update_self(client, db_session, auth_headers_employee, test_employee_user): # db_session ADICIONADO
    """Funcionário deve conseguir atualizar seus próprios dados."""
    employee_obj, _ = test_employee_user
    updated_login = "self_updated_employee_login"
    
    update_request_body = {
        "login": updated_login,
        "password": "emp_test_pass",
        "role": "funcionario"
    }

    response = client.put(
        f"/api/usuarios/{employee_obj.id}",
        json=update_request_body,
        headers=auth_headers_employee
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["login"] == updated_login

    db_session.refresh(employee_obj)
    assert employee_obj.login == updated_login


def test_employee_update_other_user_forbidden(client, auth_headers_employee, test_admin_user):
    """Funcionário NÃO deve conseguir atualizar dados de outros usuários."""
    admin_obj, _ = test_admin_user
    
    update_data = {
        "login": "forbidden_login_attempt",
        "password": "new_pass",
        "role": "admin"
    }

    response = client.put(
        f"/api/usuarios/{admin_obj.id}", # Tentando atualizar o admin
        json=update_data,
        headers=auth_headers_employee
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_delete_employee(client, db_session, auth_headers, test_employee_user):
    """Admin deve conseguir deletar um funcionário que ele gerencia."""
    employee_obj, _ = test_employee_user
    
    response = client.delete(
        f"/api/usuarios/{employee_obj.id}",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    db_deleted_user = db_session.query(UsuarioDB).filter(UsuarioDB.id == employee_obj.id).first()
    assert db_deleted_user is None
    
    db_deleted_person = db_session.query(PessoaDB).filter(PessoaDB.id == employee_obj.id_pessoa).first()
    assert db_deleted_person is None

def test_admin_cannot_delete_self(client, auth_headers, test_admin_user):
    """Admin NÃO deve conseguir deletar a si mesmo."""
    admin_obj, _ = test_admin_user
    
    response = client.delete(
        f"/api/usuarios/{admin_obj.id}",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_employee_cannot_delete_user(client, auth_headers_employee, test_admin_user):
    """Funcionário NÃO deve conseguir deletar outros usuários (nem mesmo seu admin)."""
    admin_obj, _ = test_admin_user
    
    response = client.delete(
        f"/api/usuarios/{admin_obj.id}",
        headers=auth_headers_employee
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN