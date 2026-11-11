-- ============================================================================
-- 99_validacao.sql: Consultas de Diagnostico e Auditoria do Schema Unificado
-- ============================================================================

SET search_path TO unificado, public;

-- 1. Contagem total de tabelas criadas no schema unificado
SELECT count(*) AS total_tabelas_unificado
FROM information_schema.tables
WHERE table_schema = 'unificado' AND table_type = 'BASE TABLE';

-- 2. Lista de tabelas e contagem de colunas
SELECT table_name, count(column_name) AS qtd_colunas
FROM information_schema.columns
WHERE table_schema = 'unificado'
GROUP BY table_name
ORDER BY table_name;

-- 3. Total de Foreign Keys criadas
SELECT count(*) AS total_chaves_estrangeiras
FROM information_schema.table_constraints
WHERE constraint_schema = 'unificado' AND constraint_type = 'FOREIGN KEY';

-- 4. Validacao dos ENUMs nativos criados
SELECT t.typname AS nome_enum, count(e.enumlabel) AS qtd_literais
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'unificado'
GROUP BY t.typname
ORDER BY t.typname;

-- 5. Validacao das tabelas de dominio
SELECT table_name, (xpath('/row/cnt/text()', xml_count))[1]::text::int AS registros_iniciais
FROM (
  SELECT table_name,
         query_to_xml(format('SELECT count(*) AS cnt FROM %I.%I', table_schema, table_name), false, true, '') AS xml_count
  FROM information_schema.tables
  WHERE table_schema = 'unificado' AND table_name IN (
    'tipo_formacao', 'nivel_treinamento', 'natureza', 'tipo_acao', 'tipo_projeto',
    'programa', 'tipo_apoio_financiamento', 'tipo_organizacao', 'tipo_artigo_evento',
    'tipo_livro_capitulo', 'tipo_patente_registro', 'categoria_producao_tecnica',
    'vinculo', 'situacao_participante'
  )
) t
ORDER BY table_name;
