# ddi/pipelines/builtins.py
# Este archivo importa todas las etapas del pipeline para asegurar su registro
# en el sistema al arrancar la aplicación.

from .stages import (
    analize_construct,
    architect_item,
    correct_style,
    finalize_item,
    persist,
    refine_item,
    validate_factual,
    validate_psychometric,
)
