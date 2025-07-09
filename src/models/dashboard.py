from typing import List
from pydantic import BaseModel, ConfigDict

class OcupacaoHoraData(BaseModel):
    hora: int
    acessos: int

class VisaoGeralMetrics(BaseModel):
    vagas_ocupadas: int
    total_vagas: int
    porcentagem_ocupacao: float
    entradas_hoje: int
    saidas_hoje: int
    faturamento_hoje: float

class VisaoGeralResponse(BaseModel):
    metrics: VisaoGeralMetrics
    grafico_ocupacao_hora: List[OcupacaoHoraData]

    model_config = ConfigDict(from_attributes=True)
