# ddi/pipelines/stages/correct_style.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import RefinementPatch
from ddi.pipelines.utils.stage_helpers import add_process_log_entry, handle_missing_payload

@register("correct_style")
class CorrectStyleStage(LLMStage):
    """
    Etapa que audita y propone correcciones de estilo y formato basadas
    en un conjunto de reglas mecánicas.
    """
    pydantic_schema = List[RefinementPatch]

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara el JSON de entrada para el Corrector de Estilo, enviando
        solo los textos y los hallazgos previos relevantes.
        """
        if handle_missing_payload(item, self.stage_name):
            raise ValueError("Payload ausente.")

        # Simplificamos los hallazgos previos para darle contexto al corrector
        hallazgos_simplificados = [
            {"code": p.code, "description": p.description}
            for p in item.refinement_log
        ]

        input_data = {
            "textos_por_ruta": item.payload.get_all_text_fields_by_path(),
            "hallazgos_guia": hallazgos_simplificados
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[List[RefinementPatch]], tokens_used: int):
        """
        Procesa la lista de parches de estilo y la añade al refinement_log.
        """
        if result is None:
            return

        codes_found = [p.code for p in result] if result else []

        if not result:
            comment = "OK. No se requirieron correcciones de estilo."
        else:
            # Los parches de este agente sí contienen un 'refined_value'.
            item.refinement_log.extend(result)
            comment = f"Se generaron {len(result)} parches de corrección de estilo. Códigos: {list(set(codes_found))}"

        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used,
            codes_found=codes_found
        )
