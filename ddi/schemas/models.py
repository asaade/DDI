# ddi/schemas/models.py

from __future__ import annotations
import uuid
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from .enums import ItemStatus
from .item_schemas import (
    ItemPayloadSchema,
    RefinementPatch,
    ProcessLogEntry,
    ItemGenerationParams,
    PlanDeItem
)

class Item(BaseModel):
    """
    Representa un reactivo educativo a lo largo de su ciclo de vida en el pipeline.
    Este es el objeto de datos central que se pasa entre etapas.
    """
    # --- Identificadores ---
    item_id: Optional[uuid.UUID] = Field(None, description="ID final y persistente en la BD.")
    temp_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="ID temporal para seguimiento durante la ejecución.")
    batch_id: str = Field(description="ID del lote de generación al que pertenece.")

    # --- Estado y Metadatos del Proceso ---
    status: ItemStatus = ItemStatus.PENDING
    status_comment: Optional[str] = None
    generation_params: ItemGenerationParams = Field(description="Parámetros originales de la solicitud de generación.")
    token_usage: int = Field(0, description="Uso acumulado de tokens de LLM para este ítem.")

    # --- Artefactos del Pipeline ---
    plan_de_item: Optional[PlanDeItem] = Field(None, description="El 'plano' del ítem, generado por el Analista Diagnóstico.")
    payload: Optional[ItemPayloadSchema] = Field(None, description="El contenido completo del ítem, poblado por el Arquitecto y refinado en QA.")

    # --- Historial y Trazabilidad ---
    refinement_log: List[RefinementPatch] = Field(default_factory=list, description="Log de todos los hallazgos y modificaciones de calidad.")
    process_log: List[ProcessLogEntry] = Field(default_factory=list, description="Log de las etapas del pipeline ejecutadas para este ítem.")

    # --- Datos Temporales ---
    temp_data: dict[str, Any] = Field({}, exclude=True, description="Contenedor para datos temporales entre etapas que no se persisten.")

    # --- Configuración del Modelo Pydantic ---
    model_config = ConfigDict(
        from_attributes=True,       # Permite crear el modelo desde un objeto de SQLAlchemy
        arbitrary_types_allowed=True
    )
