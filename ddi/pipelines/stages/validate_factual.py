# ddi/pipelines/stages/validate_factual.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import BaseAgentStage # Hereda de BaseAgentStage por el uso de herramientas
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import RefinementPatch
from ddi.pipelines.utils.stage_helpers import add_process_log_entry, handle_missing_payload

# Suponiendo que tienes una herramienta de búsqueda definida y registrada
# from ddi.llm.tools import web_search_tool

@register("validate_factual")
class ValidateFactualStage(BaseAgentStage):
    """
    Etapa que utiliza un agente con herramientas de búsqueda para verificar
    la exactitud factual del contenido de un ítem.
    """
    pydantic_schema = List[RefinementPatch]
    # tools = [web_search_tool] # Aquí se inyectarían las herramientas que el agente puede usar.

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara el JSON de entrada para el Auditor Factual, enviando solo
        los textos a verificar para minimizar la carga.
        """
        if handle_missing_payload(item, self.stage_name):
            raise ValueError("Payload ausente.")

        input_data = {
            "contenido": {
                "textos_a_validar": item.payload.get_all_text_fields_by_path()
            }
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[List[RefinementPatch]], tokens_used: int):
        """
        Procesa la lista de hallazgos factuales y la añade al refinement_log.
        """
        if result is None:
            return

        # Nos aseguramos de que el auditor no corrija, solo reporte.
        for hallazgo in result:
            if hallazgo.refined_value is not None:
                self.logger.warning(f"El Auditor Factual generó un 'refined_value' inesperado para el ítem {item.temp_id}. Se forzará a nulo.")
                hallazgo.refined_value = None

        codes_found = [p.code for p in result] if result else []

        if not result:
            comment = "OK. No se encontraron errores factuales."
        else:
            item.refinement_log.extend(result)
            comment = f"Se encontraron {len(result)} hallazgos factuales. Códigos: {list(set(codes_found))}"

        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used,
            codes_found=codes_found
        )
