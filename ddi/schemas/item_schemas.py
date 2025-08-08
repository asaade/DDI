# ddi/schemas/item_schemas.py

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid

from .enums import ItemStatus, DificultadEsperadaEnum, NivelCognitivoEnum

class DominioSchema(BaseModel):
    area: str
    asignatura: str
    tema: str

class AudienciaSchema(BaseModel):
    nivel_educativo: Optional[str] = None
    dificultad_esperada: DificultadEsperadaEnum = DificultadEsperadaEnum.MEDIA

class FormatoSchema(BaseModel):
    tipo_reactivo: Optional[str] = None
    numero_opciones: int = Field(4, gt=2, le=4)

class ContextoSchema(BaseModel):
    contexto_regional: Optional[str] = None
    referencia_curricular: Optional[str] = None

class IntencionEstrategicaSchema(BaseModel):
    eje_utilizado: str
    justificacion_eje: str

class ItemGenerationParams(BaseModel):
    n_items: int = Field(1, gt=0, le=10)
    dominio: DominioSchema
    objetivo_aprendizaje: str
    audiencia: AudienciaSchema
    nivel_cognitivo: NivelCognitivoEnum
    formato: FormatoSchema
    contexto: Optional[ContextoSchema] = None
    objetivo_original: Optional[str] = None
    intencion_estrategica: Optional[IntencionEstrategicaSchema] = None

class OpcionCuerpoSchema(BaseModel):
    id: str
    texto: str

class CuerpoItemSchema(BaseModel):
    estimulo: Optional[str] = None
    enunciado_pregunta: str
    opciones: List[OpcionCuerpoSchema]
    recurso_grafico: Optional[Dict[str, Any]] = None

class RetroalimentacionOpcionSchema(BaseModel):
    id: str
    es_correcta: bool
    justificacion: str

class ClaveDiagnosticoSchema(BaseModel):
    respuesta_correcta_id: str
    retroalimentacion_opciones: List[RetroalimentacionOpcionSchema]

class ErrorIdentificadoSchema(BaseModel):
    tipo_error: str
    descripcion: str

class AlineacionObjetivoSchema(BaseModel):
    es_alineado: bool
    justificacion_desviacion: Optional[str] = None

class TrazabilidadPensamientoSchema(BaseModel):
    constructo_evaluado: str
    verbo_bloom: str
    razonamiento_escenario: str
    errores_identificados: List[ErrorIdentificadoSchema]
    alineacion_objetivo: AlineacionObjetivoSchema

class MetadataCreacionSchema(BaseModel):
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    agente_generador: str

class ScoreBreakdownSchema(BaseModel):
    psychometric_content_score: int
    clarity_pedagogy_score: int
    equity_policy_score: int
    execution_style_score: int

class JustificationSchema(BaseModel):
    areas_de_mejora: str

class FinalEvaluationSchema(BaseModel):
    is_ready_for_production: bool
    score_total: int
    score_breakdown: ScoreBreakdownSchema
    justification: JustificationSchema

class ItemPayloadSchema(BaseModel):
    version: str = "1.0"
    dominio: DominioSchema
    objetivo_aprendizaje: str
    audiencia: AudienciaSchema
    nivel_cognitivo: NivelCognitivoEnum
    formato: FormatoSchema
    contexto: Optional[ContextoSchema] = None
    cuerpo_item: CuerpoItemSchema
    clave_y_diagnostico: ClaveDiagnosticoSchema
    trazabilidad_pensamiento: TrazabilidadPensamientoSchema
    metadata_creacion: MetadataCreacionSchema
    final_evaluation: Optional[FinalEvaluationSchema] = None

    def get_all_text_fields_by_path(self) -> Dict[str, str]:
        campos: Dict[str, str] = {}
        if self.cuerpo_item.estimulo:
            campos["cuerpo_item.estimulo"] = self.cuerpo_item.estimulo
        campos["cuerpo_item.enunciado_pregunta"] = self.cuerpo_item.enunciado_pregunta
        for i, opcion in enumerate(self.cuerpo_item.opciones):
            campos[f"cuerpo_item.opciones[{i}].texto"] = opcion.texto
        for i, retro in enumerate(self.clave_y_diagnostico.retroalimentacion_opciones):
             campos[f"clave_y_diagnostico.retroalimentacion_opciones[{i}].justificacion"] = retro.justificacion
        return campos

class GeneratedItemContent(BaseModel):
    cuerpo_item: CuerpoItemSchema
    clave_y_diagnostico: ClaveDiagnosticoSchema
    trazabilidad_pensamiento: TrazabilidadPensamientoSchema

class ProcessLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stage_name: str
    status: ItemStatus
    comment: Optional[str] = None
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    codes_found: Optional[List[str]] = Field(default_factory=list)

class RefinementPatch(BaseModel):
    code: str
    field_path: str
    description: str
    original_value: Optional[str] = None
    refined_value: Optional[str] = None

class GenerationResultSchema(BaseModel):
    message: str
    batch_id: str
    num_items: int

class ItemResultSchema(BaseModel):
    item_id: Optional[uuid.UUID] = None
    temp_id: uuid.UUID
    batch_id: str
    status: ItemStatus
    status_comment: Optional[str] = None
    payload: Optional[ItemPayloadSchema] = None
    process_log: List[ProcessLogEntry]
    refinement_log: List[RefinementPatch]
    model_config = ConfigDict(from_attributes=True)

class BatchStatusResultSchema(BaseModel):
    batch_id: str
    is_complete: bool
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    results: List[ItemResultSchema]


class EvidenciaNegativa(BaseModel):
    descripcion_razonamiento: str = Field(
        description="Describe el error de pensamiento específico que cometería un estudiante."
    )
    clasificacion_error: Dict[str, str] = Field(
        description="Clasifica el error según los ejes (ej. Distancia Conceptual, Origen del Fallo)."
    )
    work_product_esperado: str = Field(
        description="Describe el tipo de respuesta incorrecta (distractor) que este error produciría."
    )

class ModeloEvidencia(BaseModel):
    evidencia_positiva: Dict[str, str] = Field(
        description="Describe el razonamiento que demuestra el dominio del constructo."
    )
    evidencia_negativa: List[EvidenciaNegativa] = Field(
        description="Lista de hipótesis de error que guiarán la creación de distractores."
    )

class PlanDeItem(BaseModel):
    """
    El 'plano' psicométrico de un ítem, generado por el Analista Diagnóstico.
    Es la entrada principal para el Arquitecto Psicométrico.
    """
    faceta_a_evaluar: str = Field(
        description="La porción específica y medible del constructo que este ítem medirá."
    )
    modelo_evidencia: ModeloEvidencia
