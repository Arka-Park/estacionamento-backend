# /src/models/base.py
from sqlalchemy.orm import declarative_base

# Definimos a Base aqui, uma única vez para todo o projeto.
Base = declarative_base()