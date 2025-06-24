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
    current_admin_user: Usuario = Depends(get_current_admin_user) # Garante que apenas admins podem criar
):
    # Verifica se a pessoa já existe pelo CPF
    db_pessoa = db.query(PessoaDB).filter(PessoaDB.cpf == pessoa_data.cpf).first()
    if db_pessoa:
        # Se a pessoa já existe, verifica se já está associada a um usuário
        existing_user_for_person = db.query(UsuarioDB).filter(UsuarioDB.id_pessoa == db_pessoa.id).first()
        if existing_user_for_person:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CPF já cadastrado para outro usuário."
            )
        # Se a pessoa existe mas não tem usuário, usa a pessoa existente
    else:
        # Cria a nova pessoa se não existir
        db_pessoa = PessoaDB(**pessoa_data.model_dump())
        db.add(db_pessoa)
        db.commit()
        db.refresh(db_pessoa)

    # Verifica se o login já existe
    existing_user = db.query(UsuarioDB).filter(UsuarioDB.login == user_data.login).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login já cadastrado."
        )

    hashed_password = get_password_hash(user_data.password)

    # Cria o novo usuário
    db_user = UsuarioDB(
        id_pessoa=db_pessoa.id,
        login=user_data.login,
        senha=hashed_password,
        role=user_data.role # A role virá do payload, permitindo 'funcionario'
    )
    
    # Se o admin está criando um funcionário, atribui o admin_id
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
        # Admin pode ver seus próprios funcionários
        query = query.filter(
            (UsuarioDB.admin_id == current_user.id) | # Funcionários criados por este admin
            (UsuarioDB.id == current_user.id)          # O próprio admin
        )
    elif current_user.role == 'funcionario':
        # Funcionário só pode ver a si mesmo e talvez o seu admin, mas não outros funcionários
        # Por simplicidade, um funcionário pode ver a si mesmo.
        # Se a regra for "funcionário só vê coisas que o admin dele criou",
        # ele não necessariamente precisa ver outros funcionários ou o admin aqui.
        # Vamos permitir que um funcionário veja apenas a si mesmo por agora.
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

    # Lógica de autorização para ver um usuário específico
    if current_user.role == 'admin':
        # Admin pode ver a si mesmo, ou funcionários que ele criou
        if not (db_user.id == current_user.id or db_user.admin_id == current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este usuário")
    elif current_user.role == 'funcionario':
        # Funcionário só pode ver a si mesmo
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a ver este usuário")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    return db_user

@router.put("/{user_id}", response_model=Usuario)
async def update_user(
    user_id: int,
    user_update: UsuarioCreate, # Usando UsuarioCreate para campos atualizáveis
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    # Lógica de autorização para atualizar um usuário
    if current_user.role == 'admin':
        # Admin pode atualizar a si mesmo ou seus funcionários
        if not (db_user.id == current_user.id or db_user.admin_id == current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a atualizar este usuário")
    elif current_user.role == 'funcionario':
        # Funcionário só pode atualizar a si mesmo
        if db_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a atualizar este usuário")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    # Garante que a role não pode ser alterada de 'funcionario' para 'admin' por um funcionário
    if current_user.role == 'funcionario' and user_update.role == 'admin' and db_user.role == 'funcionario':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Funcionário não pode se promover a admin.")
    
    # Impede que um admin altere o admin_id de um funcionário
    if current_user.role == 'admin' and db_user.role == 'funcionario' and user_update.admin_id is not None and user_update.admin_id != db_user.admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin não pode alterar o admin_id de um funcionário.")


    # Atualiza os campos
    if user_update.login:
        # Verifica se o novo login já existe para outro usuário
        existing_login = db.query(UsuarioDB).filter(
            UsuarioDB.login == user_update.login, UsuarioDB.id != user_id
        ).first()
        if existing_login:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login já em uso.")
        db_user.login = user_update.login
    
    if user_update.password:
        db_user.senha = get_password_hash(user_update.password)

    db_user.role = user_update.role # Permite ao admin mudar a role, mas com a restrição acima.
    # O admin_id do funcionário será mantido como foi criado.
    # O admin_id de um admin permanece NULL.

    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin_user: Usuario = Depends(get_current_admin_user) # Apenas admins podem deletar usuários
):
    db_user = db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    # Admin não pode deletar a si mesmo (o próprio admin que está logado)
    if db_user.id == current_admin_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode deletar sua própria conta de administrador.")

    # Admin só pode deletar funcionários que ele criou
    if db_user.role == 'funcionario' and db_user.admin_id != current_admin_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para deletar este funcionário.")
    
    # Se o usuário a ser deletado é outro admin, apenas um admin "master" ou com permissão específica deveria fazer isso.
    # Por enquanto, apenas o admin criador pode deletar funcionários.
    # Deletar outro admin não é permitido aqui para evitar deleções acidentais ou não autorizadas.
    if db_user.role == 'admin':
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não é permitido deletar outros administradores.")


    # Antes de deletar o usuário, a pessoa associada a ele também deve ser deletada
    db_pessoa = db.query(PessoaDB).filter(PessoaDB.id == db_user.id_pessoa).first()
    if db_pessoa:
        db.delete(db_pessoa) # ON DELETE CASCADE na tabela usuarios garante que o usuario associado a pessoa será deletado
    
    db.delete(db_user) # Como id_pessoa tem ON DELETE CASCADE, deletar a pessoa deleta o usuario. Podemos também deletar o usuario diretamente.
    db.commit()
    return