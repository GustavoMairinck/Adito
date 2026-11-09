-- ============================================================================
-- 00_schema.sql: Criacao do Schema Unificado e Configuracao de search_path
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS unificado;

-- Configura search_path para o banco
ALTER DATABASE oraculo_db SET search_path TO unificado, public;
SET search_path TO unificado, public;
