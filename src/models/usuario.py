from typing import Optional
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship # <--- Adicione esta importação
from pydantic import BaseModel, ConfigDict, EmailStr
from .base import Base

class PessoaDB(Base):
    __tablename__ = "pessoa"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    cpf = Column(String(14), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True)

    # Adicione o relacionamento inverso para UsuarioDB
    # uselist=False porque um PessoaDB está associado a no máximo um UsuarioDB
    usuario = relationship("UsuarioDB", back_populates="pessoa", uselist=False) 

class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    id_pessoa = Column(Integer, ForeignKey("pessoa.id"), unique=True, nullable=False)
    login = Column(String(100), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'funcionario', name='user_role'), nullable=False)
    admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    # Adicione o relacionamento para PessoaDB
    # Isso permitirá o joinedload(UsuarioDB.pessoa)
    pessoa = relationship("PessoaDB", back_populates="usuario")

    # Relacionamento para administradores (opcional, se admin_id se refere a outro usuário)
    # self_referencing relationship para que um admin possa ter 'funcionarios'
    # 'remote_side=[id]' indica que 'id' é a coluna do lado remoto para este relacionamento
    funcionarios = relationship(
        "UsuarioDB",
        backref="admin", # Nome do atributo inverso no modelo UsuarioDB para se referir ao admin que criou
        remote_side=[id], # Indica que o 'id' desta classe é a coluna remota para o relacionamento
        foreign_keys=[admin_id] # Especifica qual coluna é a foreign key
    )


class UsuarioBase(BaseModel):
    login: str
    role: str = 'funcionario'

class UsuarioCreate(UsuarioBase):
    password: str
    admin_id: Optional[int] = None

class Pessoa(BaseModel): # <--- Movi Pessoa para cima, pois Usuario depende dela
    id: int
    nome: str
    cpf: str
    email: Optional[EmailStr] = None
    
    model_config = ConfigDict(from_attributes=True) # Mantenha esta configuração

class Usuario(UsuarioBase):
    id: int
    id_pessoa: int
    admin_id: Optional[int] = None
    
    # Adicione a anotação para o relacionamento da pessoa
    pessoa: Optional[Pessoa] = None # <--- Garante que os dados da Pessoa sejam incluídos na resposta

    model_config = ConfigDict(from_attributes=True) # Mantenha esta configuração

class PessoaCreate(BaseModel):
    nome: str
    cpf: str
    email: Optional[EmailStr] = None

class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"