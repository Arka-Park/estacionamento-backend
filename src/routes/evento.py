from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from ..database import get_db
from ..models import evento as models
from ..auth.dependencies import get_current_admin_user

router = APIRouter(
    prefix="/api/eventos",
    tags=["Eventos"],
    dependencies=[Depends(get_current_admin_user)]
)


@router.post("/", response_model=models.Evento, status_code=status.HTTP_201_CREATED)
def criar_evento(evento: models.EventoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo evento, garantindo que não haja sobreposição de horários.
    """
    # Validação de sobreposição de horário (a lógica correta)
    evento_sobreposto = db.query(models.EventoDB).filter(
        and_(
            models.EventoDB.id_estacionamento == evento.id_estacionamento,
            models.EventoDB.data_evento == evento.data_evento,
            models.EventoDB.hora_inicio < evento.hora_fim,
            models.EventoDB.hora_fim > evento.hora_inicio
        )
    ).first()

    if evento_sobreposto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflito de horário com o evento '{evento_sobreposto.nome}'."
        )

    # Lógica de salvar no banco
    db_evento = models.EventoDB(**evento.model_dump())
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento


@router.get("/", response_model=List[models.Evento])
def listar_eventos(db: Session = Depends(get_db)):
    """Lista todos os eventos cadastrados."""
    eventos = db.query(models.EventoDB).all()
    return eventos


@router.get("/{evento_id}", response_model=models.Evento)
def ler_evento(evento_id: int, db: Session = Depends(get_db)):
    """Obtém os dados de um evento específico pelo seu ID."""
    db_evento = db.query(models.EventoDB).filter(models.EventoDB.id == evento_id).first()
    if db_evento is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return db_evento


@router.put("/{evento_id}", response_model=models.Evento)
def atualizar_evento(evento_id: int, evento: models.EventoUpdate, db: Session = Depends(get_db)):
    """Atualiza um evento existente."""
    db_evento = db.query(models.EventoDB).filter(models.EventoDB.id == evento_id).first()
    if db_evento is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    update_data = evento.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_evento, key, value)
        
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_evento(evento_id: int, db: Session = Depends(get_db)):
    """Deleta um evento existente."""
    db_evento = db.query(models.EventoDB).filter(models.EventoDB.id == evento_id).first()
    if db_evento is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
        
    db.delete(db_evento)
    db.commit()
    return