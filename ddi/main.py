# ddi/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importaciones del proyecto DDI
from ddi.db.session import engine
from ddi.db import models
from ddi.api.v1.items_router import router as items_router
from ddi.core.config import settings

# --- IMPORTACIÓN CRUCIAL POR EFECTO SECUNDARIO ---
# Esta importación asegura que todas las etapas del pipeline se registren
# antes de que el runner intente usarlas.
from ddi.pipelines import builtins

# Crea las tablas en la base de datos al iniciar la aplicación, si no existen.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configura los orígenes permitidos para CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Incluye todas las rutas (endpoints) definidas en el router de ítems
app.include_router(items_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    """
    Endpoint raíz para una verificación de estado simple.
    """
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}
