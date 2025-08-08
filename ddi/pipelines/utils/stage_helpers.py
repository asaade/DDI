# ddi/pipelines/utils/stage_helpers.py

from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from dpath.util import set as dpath_set
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import ItemGenerationParams, ProcessLogEntry, RefinementPatch, ItemPayloadSchema
from ddi.core.log import logger

def initialize_items_for_pipeline(params: Dict[str, Any]) -> List[Item]:
    """Inicializa una lista de objetos Item para ser procesados por el pipeline."""
    try:
        gen_params = ItemGenerationParams.model_validate(params)
    except Exception as e:
        logger.error(f"Error al validar los parámetros de generación: {e}", exc_info=True)
        return []

    items_to_process: List[Item] = []
    batch_id = str(uuid.uuid4())

    for _ in range(gen_params.n_items):
        new_item = Item(
            batch_id=batch_id,
            generation_params=gen_params,
        )
        items_to_process.append(new_item)

    logger.info(f"Initialized {len(items_to_process)} items for pipeline, batch_id: {batch_id}.")
    return items_to_process

def add_process_log_entry(
    item: Item,
    stage_name: str,
    status: ItemStatus,
    comment: str,
    tokens_used: Optional[int] = None,
    duration_ms: Optional[int] = None,
    codes_found: Optional[List[str]] = None,
):
    """
    Función centralizada para actualizar el estado de un ítem y añadir una
    entrada a su 'process_log'.
    """
    log_entry = ProcessLogEntry(
        stage_name=stage_name,
        timestamp=datetime.utcnow(),
        status=status,
        comment=comment,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        codes_found=codes_found or [],
    )

    item.status = status
    item.status_comment = f"[{stage_name}]: {status.value}"
    item.process_log.append(log_entry)

    log_message = f"Item {item.temp_id}: {status.value} en '{stage_name}'. Detalle: {comment}"
    if status == ItemStatus.FATAL:
        logger.error(log_message)
    else:
        logger.info(log_message)

def handle_missing_payload(item: Item, stage_name: str) -> bool:
    """Maneja el caso donde el payload del ítem está ausente."""
    if not item.payload and stage_name not in ["analize_construct", "architect_item"]:
        comment = "Error Crítico: El payload del ítem está ausente y es requerido."
        add_process_log_entry(item, stage_name, ItemStatus.FATAL, comment)
        return True
    return False

def apply_patches(item: Item, patches: List[RefinementPatch]) -> Item:
    """
    Aplica una lista de parches a un objeto Item, modifica su payload
    y actualiza su log de refinamiento. Devuelve el ítem modificado.
    """
    if not item.payload:
        logger.warning(f"Intento de aplicar parches a un ítem sin payload: {item.temp_id}")
        return item

    if not patches:
        return item

    payload_dict = item.payload.model_dump()
    applied_patches_count = 0

    for parche in patches:
        if parche.refined_value is not None:
            try:
                dpath_set(payload_dict, parche.field_path, parche.refined_value)
                applied_patches_count += 1
            except (KeyError, IndexError):
                logger.error(f"Error al aplicar parche: Ruta no válida '{parche.field_path}' en el ítem {item.temp_id}")

    if applied_patches_count > 0:
        item.payload = ItemPayloadSchema.model_validate(payload_dict)
        item.refinement_log.extend(patches)
        logger.info(f"Aplicados {applied_patches_count} parches al ítem {item.temp_id}")

    return item
