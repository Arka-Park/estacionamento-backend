import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
import src.database
from src.routes import estacionamento as estacionamento_routes
from src.routes import auth as auth_routes
from src.routes import evento as evento_routes
from src.routes import usuario as usuario_routes
from src.routes import acesso as acesso_routes
from src.routes import dashboard as dashboard_routes

# pylint: disable=redefined-outer-name,unused-argument

MAX_RETRIES = 5
RETRY_DELAY = 5

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando a aplicação...")

    for attempt in range(MAX_RETRIES):
        try:
            with src.database.engine.connect():
                print("Conexão com o banco de dados estabelecida com sucesso!")
                break
        except OperationalError as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Tentando novamente em {RETRY_DELAY} segundos...")
                time.sleep(RETRY_DELAY)
            else:
                print("Não foi possível conectar ao banco de dados após várias tentativas.")
                raise

    yield
    print("Aplicação finalizada.")

app = FastAPI(
    title="API de Estacionamento",
    description="API para o sistema de gerenciamento de estacionamentos TPPE.",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:3000",
    "https://tppe-estacionamento.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api")
app.include_router(estacionamento_routes.router, prefix="/api")
app.include_router(evento_routes.router, prefix="/api")
app.include_router(usuario_routes.router, prefix="/api")
app.include_router(acesso_routes.router, prefix="/api")
app.include_router(dashboard_routes.router, prefix="/api")

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Verifica se a aplicação está operacional.
    """
    return {"status": "ok"}
