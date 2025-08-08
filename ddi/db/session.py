# ddi/db/session.py
"""
Módulo de sesión de base de datos para DDI: crea el motor y las sesiones.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ddi.core.config import settings

# Crea el motor de SQLAlchemy usando la URL de la base de datos desde la configuración.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, # Verifica la conexión antes de cada uso para evitar errores.
)

# Crea una fábrica de sesiones que usaremos para interactuar con la base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Función de dependencia para FastAPI.
    Se encarga de abrir una sesión de base de datos por cada solicitud,
    entregarla al endpoint y cerrarla de forma segura al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
