-- ============================================================================
-- 99_validacao.sql: Consultas de Diagnostico e Auditoria do Schema (SQLite)
-- ============================================================================

-- 1. Contagem total de tabelas criadas no banco SQLite
SELECT count(*) AS total_tabelas
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%';

-- 2. Lista de tabelas criadas
SELECT name AS tabela
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
ORDER BY name;

-- 3. Lista de views criadas
SELECT name AS view_name
FROM sqlite_master
WHERE type = 'view'
ORDER BY name;

-- 4. Verificação de integridade referencial (deve retornar 0 linhas)
PRAGMA foreign_key_check;

-- 5. Validação das 14 tabelas de domínio
SELECT 'tipo_formacao' AS tabela, count(*) AS qtd FROM tipo_formacao
UNION ALL SELECT 'nivel_treinamento', count(*) FROM nivel_treinamento
UNION ALL SELECT 'natureza', count(*) FROM natureza
UNION ALL SELECT 'tipo_acao', count(*) FROM tipo_acao
UNION ALL SELECT 'tipo_projeto', count(*) FROM tipo_projeto
UNION ALL SELECT 'programa', count(*) FROM programa
UNION ALL SELECT 'tipo_apoio_financiamento', count(*) FROM tipo_apoio_financiamento
UNION ALL SELECT 'tipo_organizacao', count(*) FROM tipo_organizacao
UNION ALL SELECT 'tipo_artigo_evento', count(*) FROM tipo_artigo_evento
UNION ALL SELECT 'tipo_livro_capitulo', count(*) FROM tipo_livro_capitulo
UNION ALL SELECT 'tipo_patente_registro', count(*) FROM tipo_patente_registro
UNION ALL SELECT 'categoria_producao_tecnica', count(*) FROM categoria_producao_tecnica
UNION ALL SELECT 'vinculo', count(*) FROM vinculo
UNION ALL SELECT 'situacao_participante', count(*) FROM situacao_participante
ORDER BY tabela;
