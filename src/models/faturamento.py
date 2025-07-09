from datetime import datetime, UTC
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class FaturamentoDB(Base):
    __tablename__ = "faturamento"
    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    data_faturamento = Column(DateTime, default=lambda: datetime.now(UTC))
    id_acesso = Column(Integer, ForeignKey("acesso.id"), nullable=False)
    acesso = relationship("AcessoDB", back_populates="faturamento")
