# ddi/pipelines/runner.py

import yaml
import asyncio
from typing import List, Dict, Any, Optional
from collections import Counter

from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.core.log import logger
from ddi.pipelines.abstractions import BaseStage
from ddi.pipelines.utils.stage_helpers import initialize_items_for_pipeline, add_process_log_entry, apply_patches
from ddi.pipelines.registry import get_full_registry
from ddi.db import crud

async def _notificar_progreso(
    ctx: Dict[str, Any],
    batch_id: str,
    items: List[Item],
    progress_fraction: float
):
    """
    Envía una actualización de progreso a través de WebSockets.
    """
    ws_manager = ctx.get("ws_manager")
    if not ws_manager:
        return

    total_items = len(items)
    status_counts = Counter(item.status.value for item in items)
    exitosos = status_counts.get(ItemStatus.PERSISTENCE_SUCCESS.value, 0)
    fallidos = status_counts.get(ItemStatus.FATAL.value, 0)
    finalizados = exitosos + fallidos
    esta_completo = finalizados == total_items

    if esta_completo:
        progress_fraction = 1.0

    datos_progreso = {
        "total_items": total_items,
        "processed_items": finalizados,
        "successful_items": exitosos,
        "failed_items": fallidos,
        "is_complete": esta_completo,
        "status_counts": dict(status_counts),
        "progress_fraction": progress_fraction
    }

    try:
        await ws_manager.send_progress_update(batch_id, datos_progreso)
        logger.info(f"Notificación de progreso enviada para el lote {batch_id}: {finalizados}/{total_items} ítems.")
    except Exception as e:
        logger.warning(f"No se pudo enviar la actualización de progreso por WebSocket para el lote {batch_id}: {e}")

async def _run_qa_cycle(items_to_validate: List[Item], qa_config: Dict, ctx: Dict[str, Any], stage_registry) -> List[Item]:
    """
    Ejecuta el ciclo de validación y refinamiento para un conjunto de ítems.
    """
    MAX_RETRIES = qa_config.get("max_retries", 3)

    processed_items_map = {item.temp_id: item for item in items_to_validate}

    for item_id, item in processed_items_map.items():
        logger.info(f"Iniciando ciclo de QA para el ítem {item.temp_id}.")
        for i in range(MAX_RETRIES):
            if item.status == ItemStatus.FATAL:
                break

            log_len_before_validation = len(item.refinement_log)

            # 1. Ejecutar todos los validadores en paralelo
            validation_tasks = []
            for validator_config in qa_config.get("validators", []):
                stage_class = stage_registry.get(validator_config["name"])
                stage_instance = stage_class(validator_config["name"], validator_config.get("params", {}), ctx)
                validation_tasks.append(stage_instance.execute([item]))

            await asyncio.gather(*validation_tasks)

            # 2. Consolidar hallazgos y parches de esta iteración
            new_patches = item.refinement_log[log_len_before_validation:]

            # Separar hallazgos (sin refined_value) de correcciones de estilo (con refined_value)
            findings_to_address = [p for p in new_patches if p.refined_value is None]
            style_corrections = [p for p in new_patches if p.refined_value is not None]

            # 3. Aplicar correcciones de estilo inmediatamente
            if style_corrections:
                item = apply_patches(item, style_corrections)

            # 4. Decidir si el ítem está aprobado
            if not findings_to_address:
                item.status = ItemStatus.VALIDATION_COMPLETE
                logger.info(f"Ítem {item.temp_id} APROBADO en el ciclo de QA {i+1}.")
                break

            # 5. Ejecutar Refinadores (si hay hallazgos de contenido)
            logger.info(f"Ítem {item.temp_id} requiere refinamiento. {len(findings_to_address)} hallazgos encontrados.")
            refiner_tasks = []
            for refiner_config in qa_config.get("refiners", []):
                stage_class = stage_registry.get(refiner_config["name"])
                stage_instance = stage_class(refiner_config["name"], refiner_config.get("params", {}), ctx)
                refiner_tasks.append(stage_instance.execute([item]))

            await asyncio.gather(*refiner_tasks)
            logger.info(f"Ítem {item.temp_id} completó el ciclo de refinamiento {i+1}.")

        if item.status != ItemStatus.VALIDATION_COMPLETE:
            item.status = ItemStatus.FATAL
            item.status_comment = f"El ítem no pasó la validación después de {MAX_RETRIES} intentos."
            add_process_log_entry(item, "qa_cycle", item.status, item.status_comment)

    return list(processed_items_map.values())


async def run(
    pipeline_config_path: str,
    user_params: Optional[Dict[str, Any]] = None,
    items_to_process: Optional[List[Item]] = None,
    ctx: Optional[Dict[str, Any]] = None,
):
    """
    Orquesta la ejecución de un pipeline de forma dinámica, basándose en
    el archivo de configuración proporcionado e implementando el ciclo de QA.
    """
    stage_registry = get_full_registry()

    if ctx is None:
        ctx = {}

    try:
        with open(pipeline_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        pipeline_stages_config = config.get("stages", [])
    except Exception as e:
        logger.error(f"Error al cargar o interpretar el archivo de configuración del pipeline: {e}")
        return

    total_stages = len(pipeline_stages_config)
    items = items_to_process or initialize_items_for_pipeline(user_params)
    if not items:
        return

    db = ctx.get("db_session")
    batch_id = items[0].batch_id if items else "ID de lote no disponible"
    logger.info(f"--- Iniciando Ejecución de Pipeline para el lote {batch_id} ---")

    await _notificar_progreso(ctx, batch_id, items, progress_fraction=0.0)

    for i, stage_config in enumerate(pipeline_stages_config):

        stage_name = stage_config.get("name") or "qa_cycle"

        try:
            processed_items = []

            if "qa_cycle" in stage_config:
                items_for_stage = [item for item in items if item.status != ItemStatus.FATAL]
                if items_for_stage:
                    logger.info(f"Ejecutando ciclo de QA. Ítems a procesar: {len(items_for_stage)}.")
                    processed_items = await _run_qa_cycle(items_for_stage, stage_config["qa_cycle"], ctx, stage_registry)

            else:
                stage_params = stage_config.get("params", {})
                listen_to_status = stage_config.get("listen_to_status_pattern")

                stage_class = stage_registry.get(stage_name)
                if not stage_class:
                    raise KeyError(f"La etapa '{stage_name}' no se encuentra en el registro.")
                stage_instance: BaseStage = stage_class(stage_name, stage_params, ctx)

                items_for_stage = [item for item in items if item.status != ItemStatus.FATAL]
                if listen_to_status:
                    items_for_stage = [item for item in items_for_stage if item.status.value.startswith(listen_to_status)]

                if items_for_stage:
                    logger.info(f"Ejecutando etapa: '{stage_name}'. Ítems a procesar: {len(items_for_stage)}.")
                    processed_items = await stage_instance.execute(items_for_stage)

            if processed_items:
                processed_map = {item.temp_id: item for item in processed_items}
                for index, item in enumerate(items):
                    if item.temp_id in processed_map:
                        items[index] = processed_map[item.temp_id]

            if db:
                crud.save_items(db=db, items=items)

            current_progress = (i + 1) / total_stages
            await _notificar_progreso(ctx, batch_id, items, progress_fraction=current_progress)

        except Exception as e:
            logger.error(f"Error inesperado durante la etapa '{stage_name}': {e}", exc_info=True)
            for item in items_for_stage:
                item.status = ItemStatus.FATAL
                item.status_comment = f"Error fatal no manejado en la etapa '{stage_name}': {str(e)}"
            await _notificar_progreso(ctx, batch_id, items, progress_fraction=1.0)

    logger.info(f"--- Pipeline finalizado para el lote {batch_id} ---")
