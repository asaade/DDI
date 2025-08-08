# ddi/schemas/enums.py

from enum import Enum

class ItemStatus(str, Enum):
    """Define los posibles estados de un ítem a lo largo del pipeline."""

    # Estados iniciales y finales
    PENDING = "pending"
    FATAL = "fatal"
    PERSISTENCE_SUCCESS = "persistence_success"

    # Estados del flujo de DDI
    ANALYSIS_SUCCESS = "analysis_success"
    GENERATION_SUCCESS = "generation_success"
    VALIDATION_COMPLETE = "validation_complete"
    REFINEMENT_COMPLETE = "refinement_complete"
    EVALUATION_COMPLETE = "evaluation_complete"


class DificultadEsperadaEnum(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


class NivelCognitivoEnum(str, Enum):
    RECORDAR = "Recordar"
    COMPRENDER = "Comprender"
    APLICAR = "Aplicar"
    ANALIZAR = "Analizar"
    EVALUAR = "Evaluar"
    CREAR = "Crear"
