from typing import Optional
from datetime import date, time
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Numeric, Date, Time, ForeignKey # 2. Importe o tipo 'Time'
from .base import Base

class EventoDB(Base):
    __tablename__ = "evento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, unique=True)
    data_evento = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)
    valor_acesso_unico = Column(Numeric(10, 2))
    id_estacionamento = Column(Integer, ForeignKey("estacionamento.id"), nullable=False)


class EventoCreate(BaseModel):
    nome: str
    data_evento: date
    hora_inicio: time
    hora_fim: time
    valor_acesso_unico: float
    id_estacionamento: int

class EventoUpdate(BaseModel):
    nome: Optional[str] = None
    data_evento: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    valor_acesso_unico: Optional[float] = None
    id_estacionamento: Optional[int] = None

class Evento(BaseModel):
    id: int
    nome: str
    data_evento: date
    hora_inicio: time
    hora_fim: time
    valor_acesso_unico: Optional[float] = None
    id_estacionamento: int

    model_config = ConfigDict(from_attributes=True)