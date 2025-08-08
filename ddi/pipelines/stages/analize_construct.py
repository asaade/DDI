# ddi/pipelines/stages/analize_construct.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import PlanDeItem
from ddi.pipelines.utils.stage_helpers import add_process_log_entry

@register("analize_construct")
class AnalyzeConstructStage(LLMStage):
    """
    Etapa que toma el objetivo de aprendizaje inicial y lo transforma
    en un Plan de Ítem estructurado, utilizando la capa de abstracción del LLM.
    """
    # La clase base LLMStage usará este schema para validar automáticamente
    # la respuesta del LLM antes de llamar a _process_llm_result.
    pydantic_schema = PlanDeItem

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara un JSON de entrada minimalista para el Analista Diagnóstico.
        """
        if not item.generation_params:
            # Esta validación es importante antes de acceder a los parámetros.
            add_process_log_entry(item, self.stage_name, ItemStatus.FATAL, "Los parámetros de generación son necesarios pero no se encontraron.")
            raise ValueError("Los parámetros de generación son necesarios para esta etapa.")

        # Construimos el objeto de entrada a medida con solo lo indispensable.
        input_data = {
            "objetivo_aprendizaje": item.generation_params.objetivo_aprendizaje,
            "dominio": item.generation_params.dominio.model_dump(),
            "audiencia": item.generation_params.audiencia.model_dump(),
            "nivel_cognitivo": item.generation_params.nivel_cognitivo.value
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[PlanDeItem], tokens_used: int):
        """
        Procesa el PlanDeItem ya validado y lo adjunta al ítem.
        """
        # La clase base ya ha manejado los errores de llamada o parseo.
        # Si 'result' es None, el estado del ítem ya se ha establecido como FATAL.
        if result is None:
            return

        # El 'result' que recibimos aquí ya es un objeto Pydantic 'PlanDeItem'
        # limpio y validado.

        # Guardamos el plan en el objeto Item para la siguiente etapa.
        item.plan_de_item = result

        comment = "Éxito. Se ha generado el Plan de Ítem."
        # Actualizamos el estado para que el runner sepa que puede pasar a la siguiente etapa.
        item.status = ItemStatus.ANALYSIS_SUCCESS
        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used
        )
