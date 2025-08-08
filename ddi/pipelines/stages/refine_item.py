# ddi/pipelines/stages/refine_item.py

import json
from typing import List, Any, Optional

from ..registry import register
from ddi.pipelines.abstractions import LLMStage
from ddi.schemas.models import Item
from ddi.schemas.enums import ItemStatus
from ddi.schemas.item_schemas import RefinementPatch
from ddi.pipelines.utils.stage_helpers import add_process_log_entry, handle_missing_payload, apply_patches

@register("refine_item")
class RefinePsychometricStage(LLMStage):
    """
    Etapa que ejecuta correcciones psicométricas y factuales en un ítem,
    basándose en los hallazgos de los validadores.
    """
    pydantic_schema = List[RefinementPatch]

    def _prepare_llm_input(self, item: Item) -> str:
        """
        Prepara el "expediente de corrección" para el Maestro Psicométrico.
        """
        if handle_missing_payload(item, self.stage_name):
            raise ValueError("Payload ausente.")

        # Filtramos los hallazgos para enviar solo los que este agente debe corregir
        # (psicométricos y factuales), excluyendo los de estilo que son manejados por otro agente.
        hallazgos_a_corregir = [
            p.model_dump() for p in item.refinement_log
            if "FORMATO_" not in p.code and "ORTOTIPOGRAFICO" not in p.code
        ]

        # Si no hay hallazgos de contenido, no es necesario llamar al LLM.
        if not hallazgos_a_corregir:
            return "" # Devolvemos un string vacío para saltar la llamada al LLM.

        input_data = {
            "contexto_psicometrico": {
                "objetivo_aprendizaje": item.payload.objetivo_aprendizaje,
                "nivel_cognitivo": item.payload.nivel_cognitivo.value,
                "audiencia": item.payload.audiencia.model_dump()
            },
            "textos_por_ruta": item.payload.get_all_text_fields_by_path(),
            "hallazgos_a_corregir": hallazgos_a_corregir
        }

        return json.dumps(input_data, ensure_ascii=False)

    async def _process_llm_result(self, item: Item, result: Optional[List[RefinementPatch]], tokens_used: int):
        """
        Procesa los parches correctivos, los aplica al payload del ítem y
        actualiza los logs.
        """
        # Si el input estaba vacío, no hubo llamada al LLM.
        if self._prepare_llm_input(item) == "":
            comment = "OK. No se encontraron hallazgos de contenido para refinar."
            add_process_log_entry(item, self.stage_name, item.status, comment, tokens_used=0)
            return

        if result is None:
            return

        if not result:
            comment = "OK. El refinador no realizó nuevas correcciones."
            add_process_log_entry(item, self.stage_name, item.status, comment, tokens_used=tokens_used)
            return

        # Aplicamos los parches de contenido al ítem
        apply_patches(item, result)

        comment = f"Éxito. {len(result)} parche(s) de contenido aplicado(s)."

        # El estado se actualiza para reflejar que el refinamiento se completó.
        # El orquestador usará este estado para decidir si re-validar.
        item.status = ItemStatus.REFINEMENT_COMPLETE
        add_process_log_entry(
            item=item,
            stage_name=self.stage_name,
            status=item.status,
            comment=comment,
            tokens_used=tokens_used,
            codes_found=[p.code for p in result]
        )
