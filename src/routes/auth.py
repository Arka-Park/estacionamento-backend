from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import usuario as models
from src import security

router = APIRouter(tags=["Autenticação"])

@router.post("/token", response_model=models.TokenData)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UsuarioDB).filter(models.UsuarioDB.login == form_data.username).first()

    if not user or not security.verify_password(form_data.password, user.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = security.create_access_token(
        data={"sub": user.login, "role": user.role}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}