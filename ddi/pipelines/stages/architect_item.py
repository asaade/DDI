# ddi/pipelines/stages/architect_item.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import GeneratedItemContent, ItemPayloadSchema
from ddi.pipelines.utils.stage_helpers import add_process_log_entry

@register("architect_item")
class ArchitectItemStage(LLMStage):
    """
    Etapa que toma un Plan de Ítem y genera el borrador completo del
    reactivo, utilizando la capa de abstracción del LLM.
    """
    # La clase base validará la salida del LLM contra este schema.
    pydantic_schema = GeneratedItemContent

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara un 'Dossier de Construcción' para el Arquitecto, combinando
        el plan de ítem con el contexto de generación relevante.
        """
        # Recuperamos el plan de la etapa anterior del objeto Item.
        if not item.plan_de_item:
            add_process_log_entry(item, self.stage_name, ItemStatus.FATAL, "El Plan de Ítem está ausente y es requerido.")
            raise ValueError("El Plan de Ítem está ausente para esta etapa.")

        if not item.generation_params:
            add_process_log_entry(item, self.stage_name, ItemStatus.FATAL, "Los parámetros de generación son necesarios pero no se encontraron.")
            raise ValueError("Los parámetros de generación son necesarios para esta etapa.")

        # Construimos el dossier con el plan y el contexto esencial.
        input_data = {
            "plan_de_item": item.plan_de_item.model_dump(),
            "contexto_de_generacion": {
                "audiencia": item.generation_params.audiencia.model_dump(),
                "dominio": item.generation_params.dominio.model_dump(),
                "restricciones": item.generation_params.restricciones.model_dump() if item.generation_params.restricciones else None
            }
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[GeneratedItemContent], tokens_used: int):
        """
        Procesa el contenido del ítem generado y lo ensambla en el payload principal.
        """
        if result is None:
            return

        # 'result' es un objeto Pydantic 'GeneratedItemContent' validado.

        # Creamos el payload final del ítem por primera vez.
        item.payload = ItemPayloadSchema(
            # Copiamos los parámetros originales de la generación.
            dominio=item.generation_params.dominio,
            objetivo_aprendizaje=item.generation_params.objetivo_aprendizaje,
            audiencia=item.generation_params.audiencia,
            nivel_cognitivo=item.generation_params.nivel_cognitivo,
            formato=item.generation_params.formato,
            contexto=item.generation_params.contexto,
            # Añadimos el contenido recién generado por el LLM.
            cuerpo_item=result.cuerpo_item,
            clave_y_diagnostico=result.clave_y_diagnostico,
            trazabilidad_pensamiento=result.trazabilidad_pensamiento,
        )

        comment = "Éxito. Ítem ensamblado, listo para las etapas de refinamiento."
        item.status = ItemStatus.GENERATION_SUCCESS
        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used
        )
