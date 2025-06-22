from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db
from src.models import estacionamento as models
from src.auth.dependencies import get_current_admin_user

class EstacionamentoUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    total_vagas: Optional[int] = None
    valor_primeira_hora: Optional[float] = None
    valor_demais_horas: Optional[float] = None
    valor_diaria: Optional[float] = None

router = APIRouter(
    prefix="/api/estacionamentos",
    tags=["Estacionamentos"],
    dependencies=[Depends(get_current_admin_user)]
)

@router.post("/", response_model=models.Estacionamento, status_code=status.HTTP_201_CREATED)
def criar_estacionamento(estacionamento: models.EstacionamentoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo estacionamento no banco de dados.
    """
    db_estacionamento_existente = db.query(models.EstacionamentoDB).filter(models.EstacionamentoDB.nome == estacionamento.nome).first()
    if db_estacionamento_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um estacionamento com este nome."
        )
    db_estacionamento = models.EstacionamentoDB(**estacionamento.model_dump())
    db.add(db_estacionamento)
    db.commit()
    db.refresh(db_estacionamento)
    return db_estacionamento


@router.get("/", response_model=List[models.Estacionamento])
def listar_estacionamentos(db: Session = Depends(get_db)):
    """
    Lista todos os estacionamentos cadastrados. Apenas administradores.
    """
    estacionamentos = db.query(models.EstacionamentoDB).order_by(models.EstacionamentoDB.id).all()
    return estacionamentos


@router.put("/{estacionamento_id}", response_model=models.Estacionamento)
def atualizar_estacionamento(estacionamento_id: int, estacionamento_update: EstacionamentoUpdate, db: Session = Depends(get_db)):
    """
    Atualiza um estacionamento existente. Apenas administradores.
    """
    db_estacionamento = db.query(models.EstacionamentoDB).filter(models.EstacionamentoDB.id == estacionamento_id).first()
    if not db_estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado")

    update_data = estacionamento_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_estacionamento, key, value)

    db.add(db_estacionamento)
    db.commit()
    db.refresh(db_estacionamento)
    return db_estacionamento


@router.delete("/{estacionamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_estacionamento(estacionamento_id: int, db: Session = Depends(get_db)):
    """
    Deleta um estacionamento específico. Apenas administradores.
    """
    estacionamento = db.query(models.EstacionamentoDB).filter(models.EstacionamentoDB.id == estacionamento_id).first()
    if not estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado")

    db.delete(estacionamento)
    db.commit()
    return