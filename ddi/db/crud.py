# ddi/db/crud.py

import logging
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from . import models as db_models
from ddi.schemas import models as pydantic_models

logger = logging.getLogger(__name__)

def save_items(db: Session, items: List[pydantic_models.Item]) -> List[db_models.ItemModel]:
    """
    Guarda o actualiza una lista de ítems Pydantic en la base de datos.
    Busca ítems existentes por item_id o temp_id para actualizarlos,
    o crea nuevos si no se encuentran.
    """
    db_items_to_return = []
    for item_pydantic in items:
        db_item = None
        # Intenta encontrar el ítem por su ID persistente primero
        if item_pydantic.item_id:
            db_item = db.query(db_models.ItemModel).filter_by(id=item_pydantic.item_id).first()
        # Si no se encuentra, busca por el ID temporal de la ejecución actual
        if not db_item:
            db_item = db.query(db_models.ItemModel).filter_by(temp_id=item_pydantic.temp_id).first()

        # Serializa los campos Pydantic a un formato compatible con JSONB
        generation_params_data = item_pydantic.generation_params.model_dump(mode="json")
        payload_data = item_pydantic.payload.model_dump(mode="json") if item_pydantic.payload else None
        process_log_data = [log.model_dump(mode="json") for log in item_pydantic.process_log]
        refinement_log_data = [patch.model_dump(mode="json") for patch in item_pydantic.refinement_log]
        plan_de_item_data = item_pydantic.plan_de_item.model_dump(mode="json") if item_pydantic.plan_de_item else None


        if db_item:
            # Actualiza los campos del ítem existente en la base de datos
            db_item.status = item_pydantic.status.value
            db_item.token_usage = item_pydantic.token_usage
            db_item.payload = payload_data
            db_item.process_log = process_log_data
            db_item.refinement_log = refinement_log_data
            db_item.generation_params = generation_params_data
            db_item.plan_de_item = plan_de_item_data

        else:
            # Crea un nuevo registro en la base de datos si el ítem no existe
            db_item = db_models.ItemModel(
                temp_id=item_pydantic.temp_id,
                batch_id=item_pydantic.batch_id,
                status=item_pydantic.status.value,
                token_usage=item_pydantic.token_usage,
                generation_params=generation_params_data,
                plan_de_item=plan_de_item_data,
                payload=payload_data,
                process_log=process_log_data,
                refinement_log=refinement_log_data,
            )
            db.add(db_item)
        db_items_to_return.append(db_item)

    try:
        # Confirma la transacción para guardar todos los cambios
        db.commit()
        # Refresca los objetos para obtener los IDs generados por la BD
        for i, db_item in enumerate(db_items_to_return):
            db.refresh(db_item)
            # Actualiza el modelo Pydantic con el ID final
            items[i].item_id = db_item.id
        return db_items_to_return
    except Exception as e:
        logger.error(f"Fallo al guardar ítems. Revirtiendo transacción. Error: {e}", exc_info=True)
        db.rollback()
        raise

# --- Otras funciones de utilidad para la API ---

def get_item(db: Session, item_id: uuid.UUID) -> Optional[db_models.ItemModel]:
    """Obtiene un único ítem de la base de datos por su ID principal."""
    return db.query(db_models.ItemModel).filter(db_models.ItemModel.id == item_id).first()

def get_items_by_batch_id(db: Session, batch_id: str) -> List[db_models.ItemModel]:
    """Obtiene todos los ítems asociados con un batch_id específico."""
    return db.query(db_models.ItemModel).filter(db_models.ItemModel.batch_id == batch_id).all()

def get_items(db: Session, skip: int = 0, limit: int = 100) -> List[db_models.ItemModel]:
    """Obtiene una lista de ítems de la base de datos con paginación."""
    return db.query(db_models.ItemModel).offset(skip).limit(limit).all()
