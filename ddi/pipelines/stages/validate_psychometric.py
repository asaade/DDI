# ddi/pipelines/stages/validate_psychometric.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import RefinementPatch
from ddi.pipelines.utils.stage_helpers import add_process_log_entry, handle_missing_payload

@register("validate_psychometric")
class ValidatePsychometricStage(LLMStage):
    """
    Etapa que audita un ítem en borrador contra una rúbrica de calidad
    psicométrica y genera un reporte de hallazgos.
    """
    pydantic_schema = List[RefinementPatch]

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara el JSON de entrada para el Validador Psicométrico.
        El input es el payload completo del ítem para una revisión holística.
        """
        if handle_missing_payload(item, self.stage_name):
            raise ValueError("Payload ausente.")

        input_data = item.payload.model_dump()

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[List[RefinementPatch]], tokens_used: int):
        """
        Procesa la lista de hallazgos y la añade al refinement_log del ítem.
        """
        if result is None:
            return

        # La regla maestra de este agente es "diagnosticar, no corregir".
        # Verificamos que el LLM haya cumplido la regla.
        for hallazgo in result:
            if hallazgo.refined_value is not None:
                self.logger.warning(f"El Validador Psicométrico generó un 'refined_value' inesperado para el ítem {item.temp_id}. Se forzará a nulo.")
                hallazgo.refined_value = None

        codes_found = [p.code for p in result] if result else []

        if not result:
            comment = "OK. No se encontraron problemas psicométricos."
        else:
            item.refinement_log.extend(result)
            comment = f"Se encontraron {len(result)} hallazgos psicométricos. Códigos: {list(set(codes_found))}"

        # Esta etapa solo añade logs. El Orquestador en runner.py decidirá
        # el siguiente estado del ítem basándose en si se encontraron hallazgos.
        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status, # Mantenemos el estado actual
            comment=comment,
            tokens_used=tokens_used,
            codes_found=codes_found
        )
