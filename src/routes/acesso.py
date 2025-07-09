# pylint: disable=too-many-arguments,line-too-long,too-many-locals, duplicate-code

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database import get_db
import src.models.acesso
from src.models import estacionamento as models_estacionamento
from src.models import evento as models_evento
from src.models import faturamento as models_faturamento
from src.models.usuario import UsuarioDB, Usuario
from src.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/acessos",
    tags=["Acessos"],
)

brazil_timezone = ZoneInfo('America/Sao_Paulo')

def check_acesso_access(
    acesso_id: int,
    db: Session,
    current_user: Usuario
) -> src.models.acesso.AcessoDB:
    db_acesso = db.query(src.models.acesso.AcessoDB).filter(src.models.acesso.AcessoDB.id == acesso_id).first()
    if not db_acesso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acesso não encontrado")

    authorized_admin_id = None
    if current_user.role == 'admin':
        authorized_admin_id = current_user.id
    elif current_user.role == 'funcionario':
        authorized_admin_id = current_user.admin_id

    if db_acesso.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar este registro de acesso.")

    return db_acesso


@router.post("/", response_model=src.models.acesso.Acesso, status_code=status.HTTP_201_CREATED)
def registrar_entrada(
    acesso_data: src.models.acesso.AcessoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role not in ['admin', 'funcionario']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para registrar acessos.")

    db_estacionamento = db.query(models_estacionamento.EstacionamentoDB).filter(
        models_estacionamento.EstacionamentoDB.id == acesso_data.id_estacionamento
    ).first()
    if not db_estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado.")

    authorized_admin_id = current_user.id if current_user.role == 'admin' else current_user.admin_id
    if db_estacionamento.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para registrar acessos neste estacionamento.")

    db.expire_all()

    vagas_ocupadas = db.query(src.models.acesso.AcessoDB).filter(
        src.models.acesso.AcessoDB.id_estacionamento == acesso_data.id_estacionamento,
        src.models.acesso.AcessoDB.hora_saida.is_(None)
    ).count()

    if vagas_ocupadas >= db_estacionamento.total_vagas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estacionamento lotado.")

    hora_entrada_local_naive = datetime.now(brazil_timezone).replace(tzinfo=None)

    active_event = db.query(models_evento.EventoDB).filter(
        and_(
            models_evento.EventoDB.id_estacionamento == acesso_data.id_estacionamento,
            models_evento.EventoDB.data_hora_inicio <= hora_entrada_local_naive,
            models_evento.EventoDB.data_hora_fim >= hora_entrada_local_naive,
            models_evento.EventoDB.admin_id == authorized_admin_id
        )
    ).first()

    tipo_acesso = 'hora'
    id_evento = None
    if active_event:
        tipo_acesso = 'evento'
        id_evento = active_event.id

    db_acesso = src.models.acesso.AcessoDB(
        **acesso_data.model_dump(),
        hora_entrada=hora_entrada_local_naive,
        tipo_acesso=tipo_acesso,
        id_evento=id_evento,
        admin_id=authorized_admin_id
    )
    db.add(db_acesso)
    db.commit()
    db.refresh(db_acesso)
    return db_acesso


@router.api_route("/{acesso_id}/saida", methods=["PUT", "OPTIONS"], response_model=src.models.acesso.Acesso)
def registrar_saida(
    acesso_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    if current_user.role not in ['admin', 'funcionario']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para registrar saídas"
        )

    db_acesso = check_acesso_access(acesso_id, db, current_user)

    if db_acesso.hora_saida:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saída já registrada para este acesso."
        )

    if db_acesso.hora_entrada.tzinfo is not None:
        db_acesso.hora_entrada = db_acesso.hora_entrada.replace(tzinfo=None)

    db_acesso.hora_saida = datetime.now(brazil_timezone).replace(tzinfo=None)

    db_estacionamento = db.query(models_estacionamento.EstacionamentoDB).filter(
        models_estacionamento.EstacionamentoDB.id == db_acesso.id_estacionamento
    ).first()
    if not db_estacionamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estacionamento associado não encontrado."
        )

    valor_total = 0.0

    if db_acesso.tipo_acesso == 'evento' and db_acesso.id_evento:
        db_evento = db.query(models_evento.EventoDB).filter(models_evento.EventoDB.id == db_acesso.id_evento).first()
        if db_evento and db_evento.valor_acesso_unico is not None:
            valor_total = float(db_evento.valor_acesso_unico)
        else:
            db_acesso.tipo_acesso = 'hora'
            time_parked = db_acesso.hora_saida - db_acesso.hora_entrada
            total_minutes = time_parked.total_seconds() / 60

            if total_minutes <= 60:
                valor_total = float(db_estacionamento.valor_primeira_hora)
            else:
                hours_to_charge = total_minutes / 60
                if total_minutes % 60 > 0:
                    hours_to_charge = int(hours_to_charge) + 1

                valor_total = float(db_estacionamento.valor_primeira_hora)
                if hours_to_charge > 1:
                    valor_total += (hours_to_charge - 1) * float(db_estacionamento.valor_demais_horas)

    elif db_acesso.tipo_acesso == 'hora':
        time_parked = db_acesso.hora_saida - db_acesso.hora_entrada
        total_hours = time_parked.total_seconds() / 3600

        if total_hours <= 24:
            if total_hours <= 1:
                valor_total = float(db_estacionamento.valor_primeira_hora)
            else:
                hours_to_charge = total_hours
                if total_hours % 1 > 0:
                    hours_to_charge = int(total_hours) + 1

                valor_total = float(db_estacionamento.valor_primeira_hora)
                if hours_to_charge > 1:
                    valor_total += (hours_to_charge - 1) * float(db_estacionamento.valor_demais_horas)
        else:
            db_acesso.tipo_acesso = 'diaria'

            total_seconds_parked = time_parked.total_seconds()
            hours_rounded_up = int(total_seconds_parked / 3600)
            if total_seconds_parked % 3600 > 0:
                hours_rounded_up += 1

            full_days = hours_rounded_up // 24
            remaining_hours_after_days = hours_rounded_up % 24

            valor_total = full_days * float(db_estacionamento.valor_diaria)

            if remaining_hours_after_days > 0:
                if remaining_hours_after_days == 1:
                    valor_total += float(db_estacionamento.valor_primeira_hora)
                else:
                    valor_total += float(db_estacionamento.valor_primeira_hora) + \
                                   (remaining_hours_after_days - 1) * float(db_estacionamento.valor_demais_horas)

    db_acesso.valor_total = round(valor_total, 2)

    novo_faturamento = models_faturamento.FaturamentoDB(
        id_acesso=db_acesso.id,
        valor=db_acesso.valor_total,
        data_faturamento=datetime.now(brazil_timezone).replace(tzinfo=None)
    )
    db.add(novo_faturamento)

    db.commit()
    db.refresh(db_acesso)
    return db_acesso


@router.get("/", response_model=List[src.models.acesso.Acesso])
def listar_acessos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    query = db.query(src.models.acesso.AcessoDB)

    if current_user.role == 'admin':
        managed_employee_ids = [
            emp.id for emp in db.query(UsuarioDB)
            .filter(UsuarioDB.admin_id == current_user.id, UsuarioDB.role == 'funcionario')
            .all()
        ]
        query = query.filter(
            (src.models.acesso.AcessoDB.admin_id == current_user.id) |
            (src.models.acesso.AcessoDB.admin_id.in_(managed_employee_ids))
        )
    elif current_user.role == 'funcionario':
        if current_user.admin_id is None:
            return []
        query = query.filter(src.models.acesso.AcessoDB.admin_id == current_user.admin_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a listar acessos.")

    acessos = query.order_by(src.models.acesso.AcessoDB.id).all()
    return acessos


@router.get("/{acesso_id}", response_model=src.models.acesso.Acesso)
def obter_acesso(
    acesso_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_acesso = check_acesso_access(acesso_id, db, current_user)
    return db_acesso
