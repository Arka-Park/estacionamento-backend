# src/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import usuario as models
from src import security
import logging # NOVO: Adicionar import para logging

router = APIRouter(tags=["Autenticação"])

# NOVO: Configurar logging para o módulo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/token", response_model=models.TokenData)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UsuarioDB).filter(models.UsuarioDB.login == form_data.username).first()

    if not user:
        logger.warning(f"Tentativa de login falha: usuário '{form_data.username}' não encontrado.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # NOVO: Adicionar bloco try-except para capturar erros na verificação da senha
    try:
        # AQUI É ONDE O ERRO PROVAVELMENTE ACONTECE
        if not security.verify_password(form_data.password, user.senha):
            logger.warning(f"Tentativa de login falha: senha incorreta para usuário '{form_data.username}'.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        # Captura qualquer exceção durante a verificação da senha e loga
        logger.error(f"Erro inesperado durante a verificação da senha para usuário '{form_data.username}': {e}", exc_info=True)
        # Re-raise como 500 para indicar um problema interno do servidor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno no servidor durante a verificação de credenciais. Verifique os logs do servidor."
        )
        
    access_token = security.create_access_token(
        data={"sub": user.login, "role": user.role}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}