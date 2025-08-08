# ddi/llm/retry.py

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Tuple, Type

def make_retry(
    exc_types: Tuple[Type[Exception], ...],
    max_retries: int = 3
):
    """
    Construye un decorador de reintentos para la librería Tenacity, parametrizado
    por los tipos de excepción que deben provocar un reintento y el número
    máximo de intentos.
    """
    return retry(
        reraise=True,  # Vuelve a lanzar la excepción original si todos los reintentos fallan
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=60), # Espera exponencial entre reintentos
        retry=retry_if_exception_type(exc_types),
    )
