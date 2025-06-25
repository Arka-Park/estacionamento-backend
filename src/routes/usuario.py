from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from src.database import get_db
from src.models.usuario import PessoaDB, UsuarioDB, UsuarioCreate, Usuario, PessoaCreate, UsuarioUpdatePayload
from src.security import get_password_hash
from src.auth.dependencies import get_current_user, get_current_admin_user

router = APIRouter(
    prefix="/usuarios",
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
        role=user_data.role
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
    query = db.query(UsuarioDB).options(joinedload(UsuarioDB.pessoa))

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
    db_user = db.query(UsuarioDB).options(joinedload(UsuarioDB.pessoa)).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if current_user.role == 'admin':
        if db_user.role == 'admin' and db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver outro administrador.")

        if db_user.role == 'funcionario' and db_user.admin_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este funcionário.")

    elif current_user.role == 'funcionario':
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este usuário")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    return db_user

@router.put("/{user_id}", response_model=Usuario)
async def update_user(
    user_id: int,
    data_to_update: UsuarioUpdatePayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_user = db.query(UsuarioDB).options(joinedload(UsuarioDB.pessoa)).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    if current_user.role == 'admin':
        if db_user.role == 'admin' and db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a editar outro administrador.")

        if db_user.role == 'funcionario' and db_user.admin_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a editar este funcionário (não criado por você).")

        if db_user.role == 'funcionario' and data_to_update.user_data.admin_id is not None and data_to_update.user_data.admin_id != db_user.admin_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin não pode alterar o admin_id de um funcionário.")

    elif current_user.role == 'funcionario':
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a atualizar este usuário")
        if data_to_update.user_data.role == 'admin' and db_user.role == 'funcionario':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Funcionário não pode se promover a admin.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    if data_to_update.user_data.login:
        existing_login = db.query(UsuarioDB).filter(
            UsuarioDB.login == data_to_update.user_data.login, UsuarioDB.id != user_id
        ).first()
        if existing_login:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login já em uso.")
        db_user.login = data_to_update.user_data.login

    if data_to_update.user_data.password:
        db_user.senha = get_password_hash(data_to_update.user_data.password)

    db_user.role = data_to_update.user_data.role

    db_pessoa = db.query(PessoaDB).filter(PessoaDB.id == db_user.id_pessoa).first()
    if db_pessoa:
        for field, value in data_to_update.pessoa_data.model_dump(exclude_unset=True).items():
            setattr(db_pessoa, field, value)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pessoa associada não encontrada.")


    db.commit()
    db.refresh(db_user)
    db.refresh(db_pessoa)

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
