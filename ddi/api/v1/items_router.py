# ddi/api/v1/items_router.py

from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session
from typing import List
import uuid

# Importaciones de la aplicación DDI
from ddi.schemas.item_schemas import (
    BatchStatusResultSchema,
    GenerationResultSchema,
    ItemGenerationParams,
    ItemResultSchema,
)
from ddi.schemas.enums import ItemStatus
from ddi.schemas.models import Item
from ddi.pipelines.runner import run as run_pipeline_async
from ddi.pipelines.utils.stage_helpers import initialize_items_for_pipeline
from ddi.core.log import logger
from ddi.db.session import get_db
from ddi.db import crud
from ddi.api.progress_utils import get_batch_progress

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, batch_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[batch_id] = websocket

    def disconnect(self, batch_id: str):
        if batch_id in self.active_connections:
            del self.active_connections[batch_id]

    async def send_progress_update(self, batch_id: str, data: dict):
        if batch_id in self.active_connections:
            await self.active_connections[batch_id].send_json(data)

manager = ConnectionManager()

@router.websocket("/ws/items/batch/{batch_id}")
async def websocket_endpoint(websocket: WebSocket, batch_id: str):
    await manager.connect(batch_id, websocket)
    logger.info(f"✅ [WS-SERVER] WebSocket CONECTADO para el lote: {batch_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(batch_id)
        logger.info(f"❌ [WS-SERVER] WebSocket DESCONECTADO para el lote: {batch_id}")

async def run_pipeline_in_background(items: List[Item], db: Session):
    batch_id = items[0].batch_id if items else "N/A"
    ctx = {"db_session": db, "ws_manager": manager}

    try:
        await run_pipeline_async(
            pipeline_config_path="config/pipeline.yml",
            items_to_process=items,
            ctx=ctx,
        )
    except Exception as e:
        logger.error(f"Error crítico al ejecutar pipeline para lote {batch_id}: {e}", exc_info=True)
    finally:
        db.close()
        logger.info(f"Sesión de base de datos cerrada para el lote {batch_id}.")

@router.post("/items/generate", response_model=GenerationResultSchema, status_code=202)
async def generate_items(
    params: ItemGenerationParams,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    logger.info(f"Recibida solicitud de generación para {params.n_items} ítems.")
    initialized_items = initialize_items_for_pipeline(params.model_dump())
    if not initialized_items:
        raise HTTPException(status_code=400, detail="Fallo al inicializar los ítems.")

    batch_id = initialized_items[0].batch_id
    try:
        crud.save_items(db=db, items=initialized_items)
    except Exception as e:
        logger.critical(f"Fallo al persistir ítems iniciales para el lote {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error de base de datos al iniciar el proceso.")

    background_tasks.add_task(run_pipeline_in_background, initialized_items, db)

    return GenerationResultSchema(
        message="Proceso de generación de ítems iniciado con éxito.",
        batch_id=batch_id,
        num_items=params.n_items,
    )

@router.get("/items/batch/{batch_id}", response_model=BatchStatusResultSchema)
def get_batch_status(
    batch_id: str, include_payloads: bool = False, db: Session = Depends(get_db)
):
    db_items = crud.get_items_by_batch_id(db, batch_id)
    if not db_items:
        raise HTTPException(status_code=404, detail="ID de lote no encontrado.")

    progress_info = get_batch_progress(batch_id, db)
    results_data: List[ItemResultSchema] = []

    for item_model in db_items:
        pydantic_item = Item.model_validate(item_model)
        payload_to_include = pydantic_item.payload if include_payloads else None

        results_data.append(
            ItemResultSchema(
                item_id=pydantic_item.item_id,
                temp_id=pydantic_item.temp_id,
                batch_id=pydantic_item.batch_id,
                status=pydantic_item.status,
                status_comment=pydantic_item.status_comment,
                payload=payload_to_include,
                process_log=pydantic_item.process_log,
                refinement_log=pydantic_item.refinement_log,
            )
        )

    return BatchStatusResultSchema(
        batch_id=batch_id,
        is_complete=progress_info.get("is_complete", False),
        total_items=progress_info.get("total_items", 0),
        processed_items=progress_info.get("processed_items", 0),
        successful_items=progress_info.get("successful_items", 0),
        failed_items=progress_info.get("failed_items", 0),
        results=results_data,
    )
