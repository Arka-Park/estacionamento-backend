# src/routes/dashboard.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, extract, union_all, literal_column
from datetime import datetime, timedelta, date, time, timezone
from typing import List, Dict, Union

from src.database import get_db
from src.models import acesso as models_acesso
from src.models import estacionamento as models_estacionamento
from src.models import faturamento as models_faturamento # Presumindo que você tem um modelo faturamento
from src.models.dashboard import OcupacaoHoraData, VisaoGeralMetrics, VisaoGeralResponse
from src.models.usuario import UsuarioDB, Usuario
from src.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

@router.get("/{estacionamento_id}", response_model=VisaoGeralResponse)
def get_visao_geral_data(
    estacionamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. Verificar permissões do usuário para o estacionamento
    db_estacionamento = db.query(models_estacionamento.EstacionamentoDB).filter(
        models_estacionamento.EstacionamentoDB.id == estacionamento_id
    ).first()

    if not db_estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado.")

    authorized_admin_id = current_user.id if current_user.role == 'admin' else current_user.admin_id
    if db_estacionamento.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar os dados deste estacionamento.")

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    # --- MÉTRICAS GERAIS (VisaoGeralMetrics) ---

    # Vagas Ocupadas (atualmente no estacionamento)
    vagas_ocupadas = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        models_acesso.AcessoDB.hora_saida.is_(None)
    ).count()
    
    total_vagas = db_estacionamento.total_vagas

    # Entradas Hoje
    entradas_hoje = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == today
    ).count()

    # Saídas Hoje
    saidas_hoje = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_saida, Date) == today
    ).count()

    # Faturamento Hoje
    # Usando a tabela faturamento para o cálculo mais preciso
    faturamento_hoje_result = db.query(func.sum(models_faturamento.FaturamentoDB.valor)).filter(
        cast(models_faturamento.FaturamentoDB.data_faturamento, Date) == today,
        models_faturamento.FaturamentoDB.id_acesso == models_acesso.AcessoDB.id,
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id
    ).scalar()
    faturamento_hoje = float(faturamento_hoje_result) if faturamento_hoje_result else 0.0

    # Porcentagem de ocupação em relação ao dia anterior (simplificado para exemplo)
    # Para um cálculo mais preciso, você precisaria de um histórico de ocupação.
    # Aqui, vamos usar um cálculo simples baseado em entradas vs saídas
    entradas_ontem = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == yesterday
    ).count()
    saidas_ontem = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_saida, Date) == yesterday
    ).count()

    # Diferença de acessos (Entradas - Saídas) de hoje vs ontem
    ocupacao_hoje_delta = entradas_hoje - saidas_hoje
    ocupacao_ontem_delta = entradas_ontem - saidas_ontem
    
    porcentagem_ocupacao = 0.0
    if ocupacao_ontem_delta != 0: # Evita divisão por zero
        porcentagem_ocupacao = ((ocupacao_hoje_delta - ocupacao_ontem_delta) / abs(ocupacao_ontem_delta)) * 100
    
    # --- GRÁFICO DE OCUPAÇÃO POR HORA (Acessos/Entradas por hora) ---
    
    # Gerar dados para as 24 horas, com 0 acessos por padrão
    acessos_por_hora_dict = {i: 0 for i in range(24)}

    # Contar acessos por hora para o dia de hoje
    # Considera entradas ocorridas dentro de cada hora do dia
    hourly_entries_today = db.query(
        extract('hour', models_acesso.AcessoDB.hora_entrada),
        func.count(models_acesso.AcessoDB.id)
    ).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == today
    ).group_by(
        extract('hour', models_acesso.AcessoDB.hora_entrada)
    ).all()

    for hour, count in hourly_entries_today:
        acessos_por_hora_dict[int(hour)] = count

    grafico_ocupacao_hora_data = [
        OcupacaoHoraData(hora=h, acessos=acessos_por_hora_dict[h]) for h in range(24)
    ]

    metrics = VisaoGeralMetrics(
        vagas_ocupadas=vagas_ocupadas,
        total_vagas=total_vagas,
        porcentagem_ocupacao=round(porcentagem_ocupacao, 2),
        entradas_hoje=entradas_hoje,
        saidas_hoje=saidas_hoje,
        faturamento_hoje=faturamento_hoje
    )

    return VisaoGeralResponse(
        metrics=metrics,
        grafico_ocupacao_hora=grafico_ocupacao_hora_data
    )