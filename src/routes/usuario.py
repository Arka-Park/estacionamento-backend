# src/routes/usuario.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.usuario import PessoaDB, UsuarioDB, UsuarioCreate, Usuario, PessoaCreate
from ..security import get_password_hash
from ..auth.dependencies import get_current_user, get_current_admin_user

router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuários"]
)

@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    pessoa_data: PessoaCreate,
    user_data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_admin_user: Usuario = Depends(get_current_admin_user)
):
    if current_admin_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Apenas administradores podem criar usuários."
        )

    db_pessoa = db.query(PessoaDB).filter(PessoaDB.cpf == pessoa_data.cpf).first()
    if db_pessoa:
        existing_user_for_person = db.query(UsuarioDB).filter(UsuarioDB.id_pessoa == db_pessoa.id).first()
        if existing_user_for_person:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CPF já cadastrado para outro usuário."
            )
    else:
        db_pessoa = PessoaDB(**pessoa_data.model_dump())
        db.add(db_pessoa)
        db.commit()
        db.refresh(db_pessoa)

    existing_user = db.query(UsuarioDB).filter(UsuarioDB.login == user_data.login).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login já cadastrado."
        )

    hashed_password = get_password_hash(user_data.password)

    db_user = UsuarioDB(
        id_pessoa=db_pessoa.id,
        login=user_data.login,
        senha=hashed_password,
        role=user_data.role # A role virá do payload, permitindo 'funcionario'
    )
    
    if user_data.role == 'funcionario':
        db_user.admin_id = current_admin_user.id
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.get("/", response_model=List[Usuario])
async def list_users(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = db.query(UsuarioDB)
    
    if current_user.role == 'admin':
        query = query.filter(
            (UsuarioDB.admin_id == current_user.id) | 
            (UsuarioDB.id == current_user.id)          
        )
    elif current_user.role == 'funcionario':
        query = query.filter(UsuarioDB.id == current_user.id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    return query.all()

@router.get("/{user_id}", response_model=Usuario)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if current_user.role == 'admin':
        if not (db_user.id == current_user.id or db_user.admin_id == current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este usuário")
    elif current_user.role == 'funcionario':
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este usuário")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    return db_user

@router.put("/{user_id}", response_model=Usuario)
async def update_user(
    user_id: int,
    user_update: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if current_user.role == 'admin':
        if not (db_user.id == current_user.id or db_user.admin_id == current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a atualizar este usuário")
    elif current_user.role == 'funcionario':
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a atualizar este usuário")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    if current_user.role == 'funcionario' and user_update.role == 'admin' and db_user.role == 'funcionario':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Funcionário não pode se promover a admin.")
    
    if current_user.role == 'admin' and db_user.role == 'funcionario' and user_update.admin_id is not None and user_update.admin_id != db_user.admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin não pode alterar o admin_id de um funcionário.")


    if user_update.login:
        existing_login = db.query(UsuarioDB).filter(
            UsuarioDB.login == user_update.login, UsuarioDB.id != user_id
        ).first()
        if existing_login:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login já em uso.")
        db_user.login = user_update.login
    
    if user_update.password:
        db_user.senha = get_password_hash(user_update.password)

    db_user.role = user_update.role # Permite ao admin mudar a role, mas com a restrição acima.

    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin_user: Usuario = Depends(get_current_admin_user)
):
    db_user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if db_user.id == current_admin_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode deletar sua própria conta de administrador.")

    if db_user.role == 'funcionario' and db_user.admin_id != current_admin_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para deletar este funcionário.")
    
    if db_user.role == 'admin':
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não é permitido deletar outros administradores.")

    db_pessoa = db.query(PessoaDB).filter(PessoaDB.id == db_user.id_pessoa).first()
    if db_pessoa:
        db.delete(db_pessoa)
    
    db.delete(db_user)
    db.commit()
    return