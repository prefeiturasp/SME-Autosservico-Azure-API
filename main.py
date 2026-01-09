from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from dotenv import load_dotenv
from config import Settings
from routers import backlog, projects

# Configuração inicial
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("app")

# Instância global das configurações
settings = Settings()

# Valida configurações
try:
    settings.validate_required_env_vars()
except ValueError as e:
    logger.error(f"Erro de configuração: {e}")
    exit(1)

# Inicializa a app
app = FastAPI(
    title="Azure DevOps Backlog API",
    description="API para extração de backlog",
    version="1.0.0"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os routers
app.include_router(backlog.router)
app.include_router(projects.router)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Azure DevOps Backlog API",
        "status": "online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port
    )
