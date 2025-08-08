# ddi/pipelines/stages/finalize_item.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import FinalEvaluationSchema
from ddi.pipelines.utils.stage_helpers import add_process_log_entry, handle_missing_payload

@register("finalize_item")
class FinalizeItemStage(LLMStage):
    """
    Etapa que invoca al Auditor Holístico para realizar una evaluación final
    del ítem y determinar si está listo para producción.
    """
    pydantic_schema = FinalEvaluationSchema

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara el JSON de entrada para el Evaluador Final.
        El input es el payload completo del ítem para una evaluación holística.
        """
        if handle_missing_payload(item, self.stage_name):
            raise ValueError("Payload ausente.")

        input_data = {
            "item_a_evaluar": item.payload.model_dump()
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[FinalEvaluationSchema], tokens_used: int):
        """
        Procesa el veredicto final, lo adjunta al payload del ítem y actualiza el estado.
        """
        if result is None:
            return

        # 'result' es un objeto Pydantic 'FinalEvaluationSchema' validado.
        item.payload.final_evaluation = result

        score = result.score_total
        verdict = "Listo para producción" if result.is_ready_for_production else "Rechazado"

        comment = f"Éxito. Puntuación final: {score}/100. Veredicto: {verdict}."

        # Este es el estado final antes de la persistencia.
        item.status = ItemStatus.EVALUATION_COMPLETE
        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used
        )
