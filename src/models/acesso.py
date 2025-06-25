from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum
from .base import Base

class AcessoDB(Base):
    __tablename__ = "acesso"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), nullable=False, index=True)
    hora_entrada = Column(DateTime, nullable=False)
    hora_saida = Column(DateTime, nullable=True)
    valor_total = Column(Numeric(10, 2), nullable=True)
    tipo_acesso = Column(Enum('evento', 'hora', 'diaria', name='tipo_acesso_enum'), nullable=False, default='hora')
    id_estacionamento = Column(Integer, ForeignKey("estacionamento.id"), nullable=False)
    id_evento = Column(Integer, ForeignKey("evento.id"), nullable=True)
    admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)


class AcessoCreate(BaseModel):
    placa: str
    id_estacionamento: int

class AcessoUpdate(BaseModel):
    hora_saida: Optional[datetime] = None
    valor_total: Optional[float] = None
    tipo_acesso: Optional[str] = None
    id_evento: Optional[int] = None

class Acesso(AcessoCreate):
    id: int
    hora_entrada: datetime
    hora_saida: Optional[datetime] = None
    valor_total: Optional[float] = None
    tipo_acesso: str
    id_evento: Optional[int] = None
    admin_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
