from typing import Optional
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from pydantic import BaseModel, ConfigDict, EmailStr
from .estacionamento import Base 

class PessoaDB(Base):
    __tablename__ = "pessoa"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    cpf = Column(String(14), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True)

class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    id_pessoa = Column(Integer, ForeignKey("pessoa.id"), unique=True, nullable=False)
    login = Column(String(100), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'funcionario', name='user_role'), nullable=False)

class UsuarioBase(BaseModel):
    login: str
    role: str = 'funcionario'

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id: int
    id_pessoa: int
    
    model_config = ConfigDict(from_attributes=True)

class PessoaCreate(BaseModel):
    nome: str
    cpf: str
    email: Optional[EmailStr] = None

class Pessoa(PessoaCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
    
class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"