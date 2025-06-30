from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class OcupacaoHoraData(BaseModel):
    hora: int # 0 a 23
    acessos: int # Número de acessos naquela hora

class VisaoGeralMetrics(BaseModel):
    vagas_ocupadas: int
    total_vagas: int
    porcentagem_ocupacao: float # Ex: 5% a mais desde ontem
    
    entradas_hoje: int
    saidas_hoje: int
    
    faturamento_hoje: float

# Modelo da resposta completa para a Visão Geral
class VisaoGeralResponse(BaseModel):
    metrics: VisaoGeralMetrics
    grafico_ocupacao_hora: List[OcupacaoHoraData]

    model_config = ConfigDict(from_attributes=True)