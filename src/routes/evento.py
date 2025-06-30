from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
from zoneinfo import ZoneInfo

from src.database import get_db
from src.models import evento as models_evento
from src.models.evento import EventoCreate, EventoUpdate, Evento
from src.models import usuario as models_usuario
from src.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/eventos",
    tags=["Eventos"],
)

brazil_timezone = ZoneInfo('America/Sao_Paulo')

@router.post("/", response_model=Evento, status_code=status.HTTP_201_CREATED)
def criar_evento(evento: EventoCreate, db: Session = Depends(get_db), current_user: models_usuario.Usuario = Depends(get_current_user)):
    # Assume que evento.data_hora_inicio e evento.data_hora_fim já são datetimes ingênuos
    # representando os componentes de hora local do frontend (Ex: YYYY-MM-DDTHH:MM:SS)
    # A coluna do DB é TIMESTAMP, que espera um datetime ingênuo.
    # Nenhuma conversão de fuso horário é necessária aqui para salvar.
    data_hora_inicio_to_save = evento.data_hora_inicio
    data_hora_fim_to_save = evento.data_hora_fim

    db_evento = models_evento.EventoDB(
        nome=evento.nome,
        id_estacionamento=evento.id_estacionamento,
        data_hora_inicio=data_hora_inicio_to_save,
        data_hora_fim=data_hora_fim_to_save,
        valor_acesso_unico=evento.valor_acesso_unico,
        admin_id=current_user.id if current_user.role == 'admin' else current_user.admin_id
    )
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento

@router.get("/{evento_id}", response_model=Evento)
def get_evento(evento_id: int, db: Session = Depends(get_db), current_user: models_usuario.Usuario = Depends(get_current_user)):
    db_evento = db.query(models_evento.EventoDB).filter(models_evento.EventoDB.id == evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    return db_evento

@router.put("/{evento_id}", response_model=Evento)
def atualizar_evento(evento_id: int, evento: EventoUpdate, db: Session = Depends(get_db), current_user: models_usuario.Usuario = Depends(get_current_user)):
    db_evento = db.query(models_evento.EventoDB).filter(models_evento.EventoDB.id == evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    
    update_data = evento.model_dump(exclude_unset=True)
    
    # Passa o datetime ingênuo diretamente, sem conversão de fuso horário
    if "data_hora_inicio" in update_data and update_data["data_hora_inicio"] is not None:
        update_data["data_hora_inicio"] = update_data["data_hora_inicio"]
    if "data_hora_fim" in update_data and update_data["data_hora_fim"] is not None:
        update_data["data_hora_fim"] = update_data["data_hora_fim"]

    for key, value in update_data.items():
        setattr(db_evento, key, value)
    
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento

@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_evento(evento_id: int, db: Session = Depends(get_db), current_user: models_usuario.Usuario = Depends(get_current_user)):
    db_evento = db.query(models_evento.EventoDB).filter(models_evento.EventoDB.id == evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado.")
    db.delete(db_evento)
    db.commit()
    return

@router.get("/estacionamento/{estacionamento_id}", response_model=List[Evento])
def listar_eventos_por_estacionamento(estacionamento_id: int, db: Session = Depends(get_db), current_user: models_usuario.Usuario = Depends(get_current_user)):
    eventos = db.query(models_evento.EventoDB).filter(models_evento.EventoDB.id_estacionamento == estacionamento_id).all()
    return eventos