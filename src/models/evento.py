from typing import Optional
from datetime import datetime # Agora usamos datetime, não date nem time
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey # Usamos DateTime
from sqlalchemy.orm import relationship

from .base import Base

class EventoDB(Base):
    __tablename__ = "evento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, unique=True)
    data_hora_inicio = Column(DateTime, nullable=False) # NOVA COLUNA
    data_hora_fim = Column(DateTime, nullable=False)     # NOVA COLUNA
    valor_acesso_unico = Column(Numeric(10, 2))
    id_estacionamento = Column(Integer, ForeignKey("estacionamento.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Assumindo que você tem relacionamentos definidos em outros lugares,
    # como em models/estacionamento.py e models/usuario.py
    # estacionamento = relationship("EstacionamentoDB", back_populates="eventos")
    # admin = relationship("UsuarioDB", back_populates="eventos_criados")


class EventoCreate(BaseModel):
    nome: str
    data_hora_inicio: datetime # Pydantic espera datetime
    data_hora_fim: datetime
    valor_acesso_unico: float
    id_estacionamento: int

class EventoUpdate(BaseModel):
    nome: Optional[str] = None
    data_hora_inicio: Optional[datetime] = None
    data_hora_fim: Optional[datetime] = None
    valor_acesso_unico: Optional[float] = None
    id_estacionamento: Optional[int] = None

class Evento(BaseModel):
    id: int
    nome: str
    data_hora_inicio: datetime
    data_hora_fim: datetime
    valor_acesso_unico: Optional[float] = None
    id_estacionamento: int
    admin_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)