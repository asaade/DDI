-- migration.sql
-- Script de migración para la tabla 'items' del proyecto DDI.

-- Elimina la tabla existente para asegurar una creación limpia.
DROP TABLE IF EXISTS items CASCADE;

-- Habilita la extensión para generación de UUIDs si no existe.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Crea la tabla 'items' con la estructura alineada al proyecto DDI.
CREATE TABLE items (
    -- Columnas de Identificación y Estado (optimizadas para búsquedas)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    temp_id UUID NOT NULL,
    batch_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    token_usage INTEGER NOT NULL DEFAULT 0,

    -- Columnas de Datos JSONB (flexibles y eficientes)
    generation_params JSONB NOT NULL,
    payload JSONB, -- Puede ser nulo al inicio del pipeline
    process_log JSONB NOT NULL DEFAULT '[]'::jsonb,
    refinement_log JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Metadatos de la fila
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger para actualizar 'updated_at' automáticamente en cada modificación.
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER set_timestamp
BEFORE UPDATE ON items
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

-- Habilita extensiones para optimizar las búsquedas en campos de texto y JSON.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- --- ÍNDICES ---

-- Índices para búsquedas clave y filtros de estado
CREATE INDEX IF NOT EXISTS idx_items_batch_id ON items (batch_id);
CREATE INDEX IF NOT EXISTS idx_items_temp_id ON items (temp_id);
CREATE INDEX IF NOT EXISTS idx_items_status ON items (status);

-- Índices GIN para búsqueda de texto completo dentro de los campos JSONB
CREATE INDEX IF NOT EXISTS idx_items_payload ON items USING gin (payload);
CREATE INDEX IF NOT EXISTS idx_items_process_log ON items USING gin (process_log);
CREATE INDEX IF NOT EXISTS idx_items_refinement_log ON items USING gin (refinement_log);

-- Índices específicos en claves del payload para consultas analíticas rápidas
CREATE INDEX IF NOT EXISTS idx_payload_dominio_tema ON items USING gin ((payload -> 'dominio' ->> 'tema') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_payload_audiencia_nivel ON items USING gin ((payload -> 'audiencia' ->> 'nivel_educativo') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_payload_nivel_cognitivo ON items USING gin ((payload ->> 'nivel_cognitivo') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_payload_formato_tipo ON items USING gin ((payload -> 'formato' ->> 'tipo_reactivo') gin_trgm_ops);
