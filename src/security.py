import os
from datetime import datetime, timedelta, timezone
from jose import jwt
from pwdlib import PasswordHash

SECRET_KEY = os.getenv("SECRET_KEY", "uma_chave_de_desenvolvimento_simples_e_longa_sem_problemas")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash."""
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera o hash de uma senha."""
    return password_hash.hash(password)

def create_access_token(data: dict):
    """Cria um novo token de acesso (JWT)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt