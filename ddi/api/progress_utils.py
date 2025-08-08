# ddi/api/progress_utils.py

from collections import Counter
from typing import Dict, Any
from sqlalchemy.orm import Session

from ddi.db import crud
from ddi.schemas.enums import ItemStatus

def get_batch_progress(batch_id: str, db: Session) -> Dict[str, Any]:
    """
    Calcula y devuelve el estado de progreso de un lote de ítems específico.

    Esta función centraliza la lógica de consulta y conteo para que pueda ser
    reutilizada por diferentes endpoints (REST y WebSocket).
    """
    # Obtenemos todos los ítems del lote desde la base de datos
    db_items = crud.get_items_by_batch_id(db, batch_id)

    total_items = len(db_items)
    if total_items == 0:
        return {
            "total_items": 0,
            "processed_items": 0,
            "successful_items": 0,
            "failed_items": 0,
            "is_complete": True,
            "status_counts": {},
            "progress_fraction": 1.0,
        }

    # Contamos la frecuencia de cada estado dentro del lote
    status_counts = Counter(item.status for item in db_items)

    # Calculamos las métricas clave
    successful_items = status_counts.get(ItemStatus.PERSISTENCE_SUCCESS.value, 0)
    failed_items = status_counts.get(ItemStatus.FATAL.value, 0)
    processed_items = successful_items + failed_items
    is_complete = processed_items == total_items

    progress_fraction = (processed_items / total_items) if total_items > 0 else 0.0
    if is_complete:
        progress_fraction = 1.0

    return {
        "total_items": total_items,
        "processed_items": processed_items,
        "successful_items": successful_items,
        "failed_items": failed_items,
        "is_complete": is_complete,
        "status_counts": dict(status_counts),
        "progress_fraction": progress_fraction,
    }
