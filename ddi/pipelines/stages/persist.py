# ddi/pipelines/stages/persist.py

from __future__ import annotations
from typing import List

from sqlalchemy.orm import Session
from ..registry import register
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.db import crud
from ddi.pipelines.abstractions import BaseStage
from ddi.pipelines.utils.stage_helpers import add_process_log_entry

@register("persist")
class PersistStage(BaseStage):
    """
    Etapa final del pipeline que persiste el estado de los ítems en la base de datos.
    No realiza llamadas a LLMs.
    """
    async def execute(self, items: List[Item]) -> List[Item]:
        if not items:
            return items

        batch_id = items[0].batch_id
        self.logger.info(f"Iniciando etapa de persistencia para {len(items)} ítems del lote {batch_id}.")

        db: Session = self.ctx.get("db_session")
        if not db:
            self.logger.error(f"Error crítico para el lote {batch_id}: Sesión de base de datos no encontrada.")
            for item in items:
                if item.status != ItemStatus.FATAL:
                    add_process_log_entry(item, self.stage_name, ItemStatus.FATAL, "No se pudo obtener la sesión de la base de datos.")
            return items

        try:
            # Añade la última entrada al log de proceso para cada ítem exitoso
            for item in items:
                if item.status != ItemStatus.FATAL:
                    add_process_log_entry(
                        item=item,
                        stage_name=self.stage_name,
                        status=ItemStatus.PERSISTENCE_SUCCESS,
                        comment="Ítem finalizado y listo para ser guardado."
                    )

            # Llama a la función CRUD para guardar o actualizar todos los ítems en una sola transacción
            crud.save_items(db=db, items=items)
            self.logger.info(f"Éxito: {len(items)} ítems del lote {batch_id} fueron persistidos en la base de datos.")

        except Exception as e:
            self.logger.critical(f"Error crítico durante la persistencia del lote {batch_id}: {e}", exc_info=True)
            for item in items:
                add_process_log_entry(
                    item=item,
                    stage_name=self.stage_name,
                    status=ItemStatus.FATAL,
                    comment=f"Fallo crítico al guardar ítem en la base de datos: {e}"
                )

        return items
