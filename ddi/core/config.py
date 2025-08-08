# ddi/core/config.py

from typing import List, Literal, Optional
from pydantic import ConfigDict, Field, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

LLMProvider = Literal["openai", "ollama", "gemini", "openrouter"]

class Settings(BaseSettings):
    """
    Define la configuración de la aplicación, cargando valores desde variables
    de entorno y un archivo .env.
    """
    PROJECT_NAME: str = "DDI - Diseño Diagnóstico Iterativo"
    API_V1_STR: str = "/api/v1"

    # Configuración de la Base de Datos
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Configuración del Proveedor de LLM por defecto
    llm_provider: LLMProvider = Field("gemini", env="LLM_PROVIDER")
    llm_model: str = Field("gemini-1.5-pro-latest", env="LLM_MODEL")
    llm_temperature: float = Field(0.5, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(8192, env="LLM_MAX_TOKENS")
    prompt_version: str = Field("2025-08-06", env="PROMPT_VERSION")

    # Claves de APIs
    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """
    Retorna una instancia cacheada de la configuración.
    """
    return Settings()

settings = get_settings()
