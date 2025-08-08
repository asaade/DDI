# ddi/db/models.py

from sqlalchemy import Column, String, Integer, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Base declarativa de SQLAlchemy a partir de la cual heredarán todos nuestros modelos.
Base = declarative_base()

class ItemModel(Base):
    """
    Modelo de SQLAlchemy que define la estructura de la tabla 'items' en la base de datos.
    """
    __tablename__ = "items"

    # Columnas de Identificación y Estado
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    temp_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    batch_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")
    token_usage = Column(Integer, nullable=False, default=0)

    # Columnas de Datos JSONB que almacenan los schemas Pydantic como JSON
    generation_params = Column(JSONB, nullable=False)
    payload = Column(JSONB, nullable=True)
    process_log = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    refinement_log = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Metadatos de la fila, manejados automáticamente por la base de datos
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
