-- ============================================================================
-- 04_fatos_views.sql: Definicao das 6 Fatos como Views Dinamicas (SQLite)
-- Single Source of Truth / 100% OLTP / Sem duplicacao em disco
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. vfact_extensao_acao_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_extensao_acao_resolved;
CREATE VIEW vfact_extensao_acao_resolved AS
SELECT
    a.id AS id_acao,
    a.id_origem AS id_origem_src,
    i.nome AS titulo_acao,
    a.processo,
    a.data_cadastro,
    CAST(strftime('%Y', a.data_cadastro) AS INTEGER) AS ano_cadastro,
    CAST(strftime('%m', a.data_cadastro) AS INTEGER) AS mes_cadastro,
    COALESCE(a.relatorio_aprovado, 0) AS relatorio_aprovado,
    CASE WHEN a.relatorio_aprovado = 1 THEN 1 ELSE 0 END AS flag_relatorio_aprovado,
    a.url_detalhe,
    ta.nome AS tipo_acao,
    nat.nome AS natureza,
    COALESCE(ga.nome, 'Não Informada') AS grande_area,
    COALESCE(ac.nome, 'Não Informada') AS area_conhecimento,
    p_coord.nome AS coordenador_nome,
    COALESCE(camp_stat.campi, 'Não Informado') AS campus,
    COALESCE(fom_stat.orgaos_fomento, 'Recurso Próprio / Sem Fomento') AS orgao_fomento,
    1 AS qtd_acoes,
    COALESCE(atv_stat.total_atividades, 0) AS qtd_atividades_vinculadas
FROM acao a
INNER JOIN iniciativa i ON a.id = i.id
LEFT JOIN tipo_acao ta ON a.id_tipo_acao = ta.id
LEFT JOIN natureza nat ON a.id_natureza = nat.id
LEFT JOIN area_conhecimento ac ON a.id_area_conhecimento = ac.id
LEFT JOIN grande_area ga ON ac.id_grande_area = ga.id
LEFT JOIN pessoa p_coord ON a.id_coordenador = p_coord.id
LEFT JOIN (
    SELECT id_acao, GROUP_CONCAT(nome_campus, '; ') AS campi
    FROM (
        SELECT DISTINCT acamp.id_acao, org_c.nome AS nome_campus
        FROM acao_campus acamp
        INNER JOIN organizacao org_c ON acamp.id_organizacao = org_c.id
    ) c_dist
    GROUP BY id_acao
) camp_stat ON a.id = camp_stat.id_acao
LEFT JOIN (
    SELECT id_acao, GROUP_CONCAT(nome_fomento, '; ') AS orgaos_fomento
    FROM (
        SELECT DISTINCT facao.id_acao, org_f.nome AS nome_fomento
        FROM fomento_acao facao
        INNER JOIN organizacao org_f ON facao.id_organizacao = org_f.id
    ) f_dist
    GROUP BY id_acao
) fom_stat ON a.id = fom_stat.id_acao
LEFT JOIN (
    SELECT id_acao, COUNT(id) AS total_atividades
    FROM atividade
    GROUP BY id_acao
) atv_stat ON a.id = atv_stat.id_acao;

-- ----------------------------------------------------------------------------
-- 2. vfact_extensao_participacao_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_extensao_participacao_resolved;
CREATE VIEW vfact_extensao_participacao_resolved AS
SELECT
    rp.id AS id_participacao,
    a.id AS id_acao,
    i.nome AS titulo_acao,
    atv.id AS id_atividade,
    atv.nome AS nome_atividade,
    COALESCE(tatv.nome, 'Não Especificado') AS tipo_atividade,
    ta.nome AS tipo_acao,
    COALESCE(camp_stat.campi, 'Não Informado') AS campus,
    COALESCE(ga.nome, 'Não Informada') AS grande_area,
    p.nome AS nome_participante,
    sp.nome AS situacao_participante,
    COALESCE(rp.certificado, 0) AS certificado_emitido,
    CASE WHEN rp.certificado = 1 THEN 1 ELSE 0 END AS flag_certificado,
    CASE WHEN LOWER(COALESCE(sp.nome, '')) LIKE 'aprovado%' THEN 1 ELSE 0 END AS flag_aprovado,
    rp.data_inicio,
    rp.data_termino,
    COALESCE(
        CAST(strftime('%Y', rp.data_inicio) AS INTEGER),
        CAST(strftime('%Y', a.data_cadastro) AS INTEGER)
    ) AS ano_participacao,
    COALESCE(rp.carga_horaria, 0.0) AS carga_horaria,
    1 AS qtd_participacoes
FROM registro_participante rp
INNER JOIN atividade atv ON rp.id_atividade = atv.id
INNER JOIN acao a ON atv.id_acao = a.id
INNER JOIN iniciativa i ON a.id = i.id
LEFT JOIN tipo_acao ta ON a.id_tipo_acao = ta.id
LEFT JOIN tipo_atividade tatv ON atv.id_tipo_atividade = tatv.id
LEFT JOIN situacao_participante sp ON rp.id_situacao = sp.id
LEFT JOIN pessoa p ON rp.id_pessoa = p.id
LEFT JOIN area_conhecimento ac ON a.id_area_conhecimento = ac.id
LEFT JOIN grande_area ga ON ac.id_grande_area = ga.id
LEFT JOIN (
    SELECT id_acao, GROUP_CONCAT(nome_campus, '; ') AS campi
    FROM (
        SELECT DISTINCT acamp.id_acao, org_c.nome AS nome_campus
        FROM acao_campus acamp
        INNER JOIN organizacao org_c ON acamp.id_organizacao = org_c.id
    ) c_dist
    GROUP BY id_acao
) camp_stat ON a.id = camp_stat.id_acao;

-- ----------------------------------------------------------------------------
-- 3. vfact_projeto_pesquisa_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_projeto_pesquisa_resolved;
CREATE VIEW vfact_projeto_pesquisa_resolved AS
SELECT
    pp.id AS id_projeto,
    pp.id_origem AS id_origem_sigpesq,
    CASE WHEN pp.id_origem IS NOT NULL THEN 'CADASTRO_COMPLETO_SIGPESQ'
         ELSE 'INFERIDO_DE_ORIENTACAO' END AS origem_registro,
    CASE WHEN pp.id_origem IS NOT NULL THEN 1 ELSE 0 END AS flag_projeto_completo,
    i.nome AS titulo_projeto,
    CAST(pp.id_natureza_projeto AS TEXT) AS natureza_projeto,
    CAST(pp.parecer_diretoria AS TEXT) AS parecer_diretoria,
    CASE WHEN pp.parecer_diretoria = 'APROVADO' THEN 1 ELSE 0 END AS flag_aprovado,
    COALESCE(pp.sigilo, 0) AS sigilo,
    pp.data_inicio,
    pp.data_fim,
    CAST(strftime('%Y', pp.data_inicio) AS INTEGER) AS ano_inicio,
    CAST(strftime('%Y', pp.data_fim) AS INTEGER) AS ano_fim,
    CASE
        WHEN pp.data_inicio IS NOT NULL AND pp.data_fim IS NOT NULL
             AND julianday(pp.data_fim) >= julianday(pp.data_inicio)
            THEN CAST(ROUND((julianday(pp.data_fim) - julianday(pp.data_inicio)) / 30.4375) AS INTEGER)
        ELSE NULL
    END AS duracao_meses_prevista,
    COALESCE(org_campus.nome, 'Não Informado') AS campus,
    ga.nome AS grande_area,
    ac.nome AS area_conhecimento,
    p_coord.nome AS coordenador_nome,
    COALESCE(tit.nome, 'Não Informada') AS titulacao_coordenador,
    pp.palavras_chave,
    COALESCE(parc_stat.parceiros, 'Sem Parceiro Demandante') AS parceiros_demandantes,
    1 AS qtd_projetos,
    COALESCE(plano_stat.total_planos, 0) AS qtd_planos_trabalho
FROM projeto_pesquisa pp
INNER JOIN iniciativa i ON pp.id = i.id
LEFT JOIN organizacao org_campus ON pp.id_campus = org_campus.id
LEFT JOIN area_conhecimento ac ON pp.id_area_conhecimento = ac.id
LEFT JOIN grande_area ga ON ac.id_grande_area = ga.id
LEFT JOIN pesquisador pesq ON pp.id_coordenador = pesq.id
LEFT JOIN pessoa p_coord ON pesq.id = p_coord.id
LEFT JOIN titulacao tit ON pesq.id_titulacao = tit.id
LEFT JOIN (
    SELECT id_projeto_pesquisa, COUNT(id) AS total_planos
    FROM plano_trabalho
    GROUP BY id_projeto_pesquisa
) plano_stat ON pp.id = plano_stat.id_projeto_pesquisa
LEFT JOIN (
    SELECT id_projeto_pesquisa, GROUP_CONCAT(nome_parceiro, '; ') AS parceiros
    FROM (
        SELECT DISTINCT pdp.id_projeto_pesquisa, org_p.nome AS nome_parceiro
        FROM parceiro_demandante_projeto pdp
        INNER JOIN organizacao org_p ON pdp.id_organizacao = org_p.id
    ) p_dist
    GROUP BY id_projeto_pesquisa
) parc_stat ON pp.id = parc_stat.id_projeto_pesquisa;

-- ----------------------------------------------------------------------------
-- 4. vfact_orientacao_bolsa_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_orientacao_bolsa_resolved;
CREATE VIEW vfact_orientacao_bolsa_resolved AS
SELECT
    o.id AS id_orientacao,
    o.id_origem AS id_origem_sigpesq,
    o.ano,
    COALESCE(prog.nome, 'Não Especificado') AS programa_fomento,
    CAST(o.modalidade AS TEXT) AS modalidade,
    CAST(o.gerenciamento AS TEXT) AS gerenciamento,
    COALESCE(ed.titulo, 'Sem Edital Vinculado') AS titulo_edital,
    pt.codigo AS codigo_plano_trabalho,
    pt.titulo AS titulo_plano_trabalho,
    i_proj.nome AS titulo_projeto,
    COALESCE(org_campus.nome, 'Não Informado') AS campus,
    COALESCE(org_fin.nome, 'Recurso Institucional Ifes') AS agencia_financiadora,
    ga.nome AS grande_area,
    ac.nome AS area_conhecimento,
    p_orientador.nome AS nome_orientador,
    tit_orientador.nome AS titulacao_orientador,
    p_orientado.nome AS nome_orientado,
    nt.nome AS nivel_treinamento_aluno,
    c_aluno.nome AS curso_orientado,
    o.data_inicio,
    o.data_fim,
    CAST(ROUND((julianday(o.data_fim) - julianday(o.data_inicio)) / 30.4375) AS INTEGER) AS duracao_meses,
    CASE
        WHEN o.cancelado = 1 AND o.data_cancelado IS NOT NULL AND o.data_inicio IS NOT NULL
             AND julianday(o.data_cancelado) <= julianday(o.data_inicio)
            THEN 0
        WHEN o.cancelado = 1 AND o.data_cancelado IS NOT NULL AND o.data_inicio IS NOT NULL
            THEN MAX(1, CAST(ROUND((
                CASE
                    WHEN o.data_fim IS NOT NULL AND julianday(o.data_fim) < julianday(o.data_cancelado)
                        THEN julianday(o.data_fim)
                    ELSE julianday(o.data_cancelado)
                END - julianday(o.data_inicio)
            ) / 30.4375) AS INTEGER))
        WHEN o.data_inicio IS NOT NULL AND o.data_fim IS NOT NULL
            THEN MAX(1, CAST(ROUND((julianday(o.data_fim) - julianday(o.data_inicio)) / 30.4375) AS INTEGER))
        ELSE 12
    END AS duracao_meses_efetiva,
    COALESCE(o.valor_bolsa, 0.00) AS valor_bolsa_mensal,
    CASE
        WHEN o.modalidade <> 'BOLSISTA' THEN 0.00
        WHEN o.cancelado = 1 AND o.data_cancelado IS NOT NULL AND o.data_inicio IS NOT NULL
             AND julianday(o.data_cancelado) <= julianday(o.data_inicio)
            THEN 0.00
        WHEN o.cancelado = 1 AND o.data_cancelado IS NOT NULL AND o.data_inicio IS NOT NULL
            THEN COALESCE(o.valor_bolsa, 0.00) * MAX(1, ROUND((
                CASE
                    WHEN o.data_fim IS NOT NULL AND julianday(o.data_fim) < julianday(o.data_cancelado)
                        THEN julianday(o.data_fim)
                    ELSE julianday(o.data_cancelado)
                END - julianday(o.data_inicio)
            ) / 30.4375))
        WHEN o.data_inicio IS NOT NULL AND o.data_fim IS NOT NULL
            THEN COALESCE(o.valor_bolsa, 0.00) * MAX(1, ROUND((julianday(o.data_fim) - julianday(o.data_inicio)) / 30.4375))
        ELSE COALESCE(o.valor_bolsa, 0.00) * 12
    END AS investimento_total_estimado,
    CASE
        WHEN o.modalidade = 'BOLSISTA' AND o.data_inicio IS NOT NULL AND o.data_fim IS NOT NULL
            THEN COALESCE(o.valor_bolsa, 0.00) * MAX(1, ROUND((julianday(o.data_fim) - julianday(o.data_inicio)) / 30.4375))
        WHEN o.modalidade = 'BOLSISTA'
            THEN COALESCE(o.valor_bolsa, 0.00) * 12
        ELSE 0.00
    END AS investimento_previsto_original,
    COALESCE(o.cancelado, 0) AS cancelado,
    CASE WHEN o.cancelado = 1 THEN 1 ELSE 0 END AS flag_cancelado,
    o.nome_cancelador,
    o.data_cancelado,
    COALESCE(o.relatorio_enviado, 0) AS relatorio_enviado,
    CASE WHEN o.relatorio_enviado = 1 THEN 1 ELSE 0 END AS flag_relatorio_enviado,
    1 AS qtd_orientacoes
FROM orientacao o
INNER JOIN plano_trabalho pt ON o.id_plano_trabalho = pt.id
INNER JOIN projeto_pesquisa pp ON pt.id_projeto_pesquisa = pp.id
INNER JOIN iniciativa i_proj ON pp.id = i_proj.id
LEFT JOIN edital ed ON pt.id_edital = ed.id
LEFT JOIN programa prog ON o.id_programa = prog.id
LEFT JOIN pesquisador pesq ON o.id_orientador = pesq.id
LEFT JOIN pessoa p_orientador ON pesq.id = p_orientador.id
LEFT JOIN titulacao tit_orientador ON pesq.id_titulacao = tit_orientador.id
LEFT JOIN estudante est ON o.id_orientado = est.id
LEFT JOIN pessoa p_orientado ON est.id = p_orientado.id
LEFT JOIN nivel_treinamento nt ON est.id_nivel_treinamento = nt.id
LEFT JOIN curso c_aluno ON est.id_curso = c_aluno.id
LEFT JOIN organizacao org_campus ON o.id_campus = org_campus.id
LEFT JOIN organizacao org_fin ON o.id_financiador = org_fin.id
LEFT JOIN area_conhecimento ac ON COALESCE(pt.id_area_conhecimento, pp.id_area_conhecimento) = ac.id
LEFT JOIN grande_area ga ON ac.id_grande_area = ga.id;

-- ----------------------------------------------------------------------------
-- 5. vfact_producao_cientifica_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_producao_cientifica_resolved;
CREATE VIEW vfact_producao_cientifica_resolved AS
SELECT
    ap.id_producao,
    ap.id_pessoa_lattes,
    prod.titulo AS titulo_producao,
    prod.ano,
    CASE
        WHEN art.id IS NOT NULL THEN 'ARTIGO_OU_EVENTO'
        WHEN liv.id IS NOT NULL THEN 'LIVRO_OU_CAPITULO'
        WHEN pat.id IS NOT NULL THEN 'PATENTE_REGISTRO'
        WHEN tec.id IS NOT NULL THEN 'TECNICA_ARTISTICA'
        ELSE 'OUTRA_PRODUCAO'
    END AS tipo_macro_producao,
    COALESCE(tart.nome, tliv.nome, tpat.nome, ctec.nome, 'Não Classificado') AS subtipo_producao,
    COALESCE(art.veiculo_revista_evento, liv.editora, pat.pais, tec.subtipo) AS veiculo_publicacao,
    art.doi,
    art.issn_isbn,
    art.natureza AS natureza_artigo,
    p.nome AS nome_autor,
    plat.id_lattes AS id_lattes_autor,
    CASE
        WHEN org_vinc.id IS NOT NULL AND org_vinc.id_organizacao_pai IS NOT NULL
            THEN org_vinc.nome
        ELSE 'Externo / Não Vinculado'
    END AS campus,
    COALESCE(org_vinc.nome, 'Não Vinculada') AS instituicao_vinculo,
    CASE WHEN tart.nome = 'ARTIGO_PERIODICO' THEN 1 ELSE 0 END AS flag_artigo_periodico,
    CASE WHEN pat.id IS NOT NULL THEN 1 ELSE 0 END AS flag_patente_software,
    CASE WHEN ctec.nome = 'SOFTWARE_SEM_PATENTE' THEN 1 ELSE 0 END AS flag_software_sem_patente,
    CASE
        WHEN ROW_NUMBER() OVER (PARTITION BY ap.id_producao ORDER BY ap.id_pessoa_lattes) = 1
            THEN 1
        ELSE 0
    END AS flag_obra_unica,
    1 AS qtd_autorias
FROM autoria_producao ap
INNER JOIN producao prod ON ap.id_producao = prod.id
LEFT JOIN artigo_trabalho_evento art ON prod.id = art.id
LEFT JOIN tipo_artigo_evento tart ON art.id_tipo_publicacao = tart.id
LEFT JOIN livro_capitulo liv ON prod.id = liv.id
LEFT JOIN tipo_livro_capitulo tliv ON liv.id_tipo_livro_capitulo = tliv.id
LEFT JOIN patente_registro pat ON prod.id = pat.id
LEFT JOIN tipo_patente_registro tpat ON pat.id_tipo_patente_registro = tpat.id
LEFT JOIN producao_tecnica_artistica_bibliografica tec ON prod.id = tec.id
LEFT JOIN categoria_producao_tecnica ctec ON tec.id_categoria = ctec.id
INNER JOIN pessoa_lattes plat ON ap.id_pessoa_lattes = plat.id
INNER JOIN pessoa p ON plat.id = p.id
LEFT JOIN pesquisador pesq ON p.id = pesq.id
LEFT JOIN organizacao org_vinc ON pesq.id_organizacao = org_vinc.id;

-- ----------------------------------------------------------------------------
-- 6. vfact_grupo_pesquisa_membro_resolved
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vfact_grupo_pesquisa_membro_resolved;
CREATE VIEW vfact_grupo_pesquisa_membro_resolved AS
SELECT
    mgc.id AS id_membro_grupo,
    gp.id AS id_grupo_pesquisa,
    gp.nome AS nome_grupo,
    gp.sigla AS sigla_grupo,
    CAST(gpc.situacao_grupo AS TEXT) AS situacao_grupo,
    gpc.ano_formacao,
    gp.url_cnpq,
    COALESCE(org_campus.nome, 'Campus Não Informado') AS campus,
    ga.nome AS grande_area,
    ac.nome AS area_conhecimento,
    p.nome AS nome_membro,
    COALESCE(pap.nome, 'Pesquisador') AS papel_membro,
    CAST(mgc.status_participacao AS TEXT) AS status_participacao,
    CASE WHEN mgc.status_participacao = 'ATIVO' THEN 1 ELSE 0 END AS flag_ativo,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM lideranca_grupo_pesquisa lgp
            WHERE lgp.id_grupo_pesquisa = gp.id
              AND lgp.id_pesquisador = p.id
        ) OR LOWER(COALESCE(pap.nome, '')) LIKE '%líder%'
          OR LOWER(COALESCE(pap.nome, '')) LIKE '%lider%' THEN 1
        ELSE 0
    END AS flag_lider,
    COALESCE(tit.nome, 'Não Informada') AS titulacao_membro,
    mg.data_inicio,
    mg.data_fim,
    CASE
        WHEN mg.data_inicio IS NOT NULL
             AND julianday(COALESCE(mg.data_fim, date('now'))) >= julianday(mg.data_inicio)
            THEN CAST(julianday(COALESCE(mg.data_fim, date('now'))) - julianday(mg.data_inicio) AS INTEGER)
        ELSE NULL
    END AS tempo_participacao_dias,
    1 AS qtd_membros
FROM membro_grupo_cnpq mgc
INNER JOIN membro_grupo mg ON mgc.id = mg.id
INNER JOIN grupo_pesquisa_cnpq gpc ON mgc.id_grupo_pesquisa_cnpq = gpc.id
INNER JOIN grupo_pesquisa gp ON gpc.id = gp.id
INNER JOIN pessoa p ON mgc.id_pessoa = p.id
LEFT JOIN papel pap ON mg.id_papel = pap.id
LEFT JOIN pesquisador pesq ON p.id = pesq.id
LEFT JOIN titulacao tit ON pesq.id_titulacao = tit.id
LEFT JOIN organizacao org_campus ON gpc.id_campus = org_campus.id
LEFT JOIN area_conhecimento ac ON gp.id_area_conhecimento = ac.id
LEFT JOIN grande_area ga ON ac.id_grande_area = ga.id;
