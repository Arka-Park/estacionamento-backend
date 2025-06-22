from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import estacionamento as estacionamento_routes
from src.models import usuario as usuario_model
from src.routes import auth as auth_routes
from src.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI): # pylint: disable=W0613, W0621
    print("Iniciando a aplicação ...")
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

app.include_router(estacionamento_routes.router)
app.include_router(auth_routes.router)

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Verifica se a aplicação está operacional.
    """
    return {"status": "ok"}
