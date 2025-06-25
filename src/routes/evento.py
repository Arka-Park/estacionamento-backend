# src/routes/evento.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date, time # Importar date e time
from ..database import get_db
from ..models import evento as models
from ..models.usuario import UsuarioDB, Usuario # Importar UsuarioDB e Usuario
from ..auth.dependencies import get_current_user, get_current_admin_user # get_current_user agora será mais usado

router = APIRouter(
    prefix="/eventos",
    tags=["Eventos"],
    # Removendo a dependência global de admin
    # dependencies=[Depends(get_current_admin_user)]
)

# Helper para verificar permissão de acesso a um evento
def check_evento_access(
    evento_id: int, 
    db: Session, 
    current_user: Usuario
) -> models.EventoDB:
    db_evento = db.query(models.EventoDB).filter(models.EventoDB.id == evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")

    authorized_admin_id = None
    if current_user.role == 'admin':
        authorized_admin_id = current_user.id
    elif current_user.role == 'funcionario':
        authorized_admin_id = current_user.admin_id
    
    # Se o evento não tem admin_id ou se o admin_id não corresponde
    if db_evento.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar este evento.")
    
    return db_evento


@router.post("/", response_model=models.Evento, status_code=status.HTTP_201_CREATED)
def criar_evento(
    evento: models.EventoCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user) # Exige qualquer usuário logado
):
    """
    Cria um novo evento, garantindo que não haja sobreposição de horários. Apenas administradores.
    """
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Apenas administradores podem criar eventos."
        )

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

    # Lógica de salvar no banco, atribuindo o admin_id
    db_evento = models.EventoDB(**evento.model_dump(), admin_id=current_user.id)
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento


@router.get("/", response_model=List[models.Evento])
def listar_eventos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user) # Exige qualquer usuário logado
):
    """
    Lista os eventos visíveis para o usuário logado.
    Administradores veem os seus e os de seus funcionários.
    Funcionários veem os do seu administrador.
    """
    query = db.query(models.EventoDB)

    if current_user.role == 'admin':
        # Admin pode ver seus próprios eventos
        # e os eventos criados por funcionários que ele gerencia
        
        # Obter IDs dos funcionários que este admin gerencia
        managed_employee_ids = [
            emp.id for emp in db.query(UsuarioDB)
            .filter(UsuarioDB.admin_id == current_user.id, UsuarioDB.role == 'funcionario')
            .all()
        ]
        
        query = query.filter(
            (models.EventoDB.admin_id == current_user.id) |  # Eventos criados pelo próprio admin
            (models.EventoDB.admin_id.in_(managed_employee_ids)) # Eventos criados por funcionários dele
        )
    elif current_user.role == 'funcionario':
        # Funcionário só pode ver eventos cujo admin_id é o ID do seu próprio admin
        if current_user.admin_id is None:
            return [] # Caso raro de funcionário sem admin_id atribuído
        query = query.filter(models.EventoDB.admin_id == current_user.admin_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a listar eventos.")

    eventos = query.all()
    return eventos


@router.get("/{evento_id}", response_model=models.Evento)
def ler_evento(
    evento_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém os dados de um evento específico pelo seu ID, com controle de acesso.
    """
    db_evento = check_evento_access(evento_id, db, current_user)
    return db_evento


@router.put("/{evento_id}", response_model=models.Evento)
def atualizar_evento(
    evento_id: int, 
    evento_update: models.EventoUpdate, # Usando EventoUpdate como antes
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza um evento existente, com controle de acesso.
    """
    db_evento = check_evento_access(evento_id, db, current_user)
    
    update_data = evento_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_evento, key, value)
        
    db.add(db_evento)
    db.commit()
    db.refresh(db_evento)
    return db_evento


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_evento(
    evento_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Deleta um evento existente, com controle de acesso.
    """
    db_evento = check_evento_access(evento_id, db, current_user)
        
    db.delete(db_evento)
    db.commit()
    return