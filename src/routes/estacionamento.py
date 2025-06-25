from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db
from src.models import estacionamento as models
from src.models.usuario import UsuarioDB, Usuario
from src.auth.dependencies import get_current_user

class EstacionamentoUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    total_vagas: Optional[int] = None
    valor_primeira_hora: Optional[float] = None
    valor_demais_horas: Optional[float] = None
    valor_diaria: Optional[float] = None

router = APIRouter(
    prefix="/estacionamentos",
    tags=["Estacionamentos"],
)

def check_estacionamento_access(
    estacionamento_id: int,
    db: Session,
    current_user: Usuario
) -> models.EstacionamentoDB:
    db_estacionamento = db.query(models.EstacionamentoDB).filter(models.EstacionamentoDB.id == estacionamento_id).first()
    if not db_estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado")

    authorized_admin_id = None
    if current_user.role == 'admin':
        authorized_admin_id = current_user.id
    elif current_user.role == 'funcionario':
        authorized_admin_id = current_user.admin_id

    if db_estacionamento.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar este estacionamento.")

    return db_estacionamento

@router.post("/", response_model=models.Estacionamento, status_code=status.HTTP_201_CREATED)
def criar_estacionamento(
    estacionamento: models.EstacionamentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cria um novo estacionamento no banco de dados. Apenas administradores.
    """
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar estacionamentos."
        )

    db_estacionamento_existente = db.query(models.EstacionamentoDB).filter(models.EstacionamentoDB.nome == estacionamento.nome).first()
    if db_estacionamento_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um estacionamento com este nome."
        )

    db_estacionamento = models.EstacionamentoDB(**estacionamento.model_dump(), admin_id=current_user.id)
    db.add(db_estacionamento)
    db.commit()
    db.refresh(db_estacionamento)
    return db_estacionamento


@router.get("/", response_model=List[models.Estacionamento])
def listar_estacionamentos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista os estacionamentos visíveis para o usuário logado.
    Administradores veem os seus e os de seus funcionários.
    Funcionários veem os do seu administrador.
    """
    query = db.query(models.EstacionamentoDB)

    if current_user.role == 'admin':
        managed_employee_ids = [
            emp.id for emp in db.query(UsuarioDB)
            .filter(UsuarioDB.admin_id == current_user.id, UsuarioDB.role == 'funcionario')
            .all()
        ]

        query = query.filter(
            (models.EstacionamentoDB.admin_id == current_user.id) |
            (models.EstacionamentoDB.admin_id.in_(managed_employee_ids))
        )
    elif current_user.role == 'funcionario':
        if current_user.admin_id is None:
            return []
        query = query.filter(models.EstacionamentoDB.admin_id == current_user.admin_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a listar estacionamentos.")

    estacionamentos = query.order_by(models.EstacionamentoDB.id).all()
    return estacionamentos


@router.get("/{estacionamento_id}", response_model=models.Estacionamento)
def obter_estacionamento(
    estacionamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém um estacionamento específico pelo ID, com controle de acesso.
    """
    db_estacionamento = check_estacionamento_access(estacionamento_id, db, current_user)
    return db_estacionamento


@router.put("/{estacionamento_id}", response_model=models.Estacionamento)
def atualizar_estacionamento(
    estacionamento_id: int,
    estacionamento_update: EstacionamentoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza um estacionamento existente, com controle de acesso.
    """
    db_estacionamento = check_estacionamento_access(estacionamento_id, db, current_user)

    update_data = estacionamento_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_estacionamento, key, value)

    db.add(db_estacionamento)
    db.commit()
    db.refresh(db_estacionamento)
    return db_estacionamento


@router.delete("/{estacionamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_estacionamento(
    estacionamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Deleta um estacionamento específico, com controle de acesso.
    """
    estacionamento = check_estacionamento_access(estacionamento_id, db, current_user)

    db.delete(estacionamento)
    db.commit()
