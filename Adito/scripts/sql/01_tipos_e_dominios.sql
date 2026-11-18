-- ============================================================================
-- 01_tipos_e_dominios.sql: ENUMs (CHECK constraints) e Tabelas de Domínio (SQLite)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Definições de ENUMs (Referência para validação e constraints CHECK)
-- ----------------------------------------------------------------------------

-- CREATE TYPE unificado.tipo_uf AS ENUM (
--     'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
--     'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
--     'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO', 'EXTERIOR'
-- );

-- CREATE TYPE unificado.tipo_status_ciclo AS ENUM (
--     'EM_ANDAMENTO', 'CONCLUIDO'
-- );

-- CREATE TYPE unificado.tipo_status_participacao AS ENUM (
--     'ATIVO', 'EGRESSO'
-- );

-- CREATE TYPE unificado.tipo_natureza_projeto AS ENUM (
--     'PESQUISA_APLICADA', 'PESQUISA_BASICA'
-- );

-- CREATE TYPE unificado.tipo_modalidade_orientacao AS ENUM (
--     'POS_DOUTORADO', 'DOUTORADO', 'MESTRADO', 'ESPECIALIZACAO',
--     'TCC', 'INICIACAO_CIENTIFICA', 'OUTROS'
-- );

-- CREATE TYPE unificado.tipo_modalidade_banca AS ENUM (
--     'DOUTORADO', 'MESTRADO', 'QUALIFICACAO_DOUTORADO',
--     'QUALIFICACAO_MESTRADO', 'GRADUACAO', 'OUTRAS'
-- );

-- CREATE TYPE unificado.tipo_papel_orientacao AS ENUM (
--     'ORIENTADOR', 'COORIENTADOR', 'SUPERVISOR'
-- );

-- CREATE TYPE unificado.tipo_papel_projeto AS ENUM (
--     'COORDENADOR', 'INTEGRANTE'
-- );

-- CREATE TYPE unificado.tipo_papel_evento AS ENUM (
--     'PARTICIPACAO', 'ORGANIZACAO'
-- );

-- CREATE TYPE unificado.tipo_nivel_proficiencia AS ENUM (
--     'BEM', 'RAZOAVELMENTE', 'POUCO'
-- );

-- CREATE TYPE unificado.tipo_parecer_diretoria AS ENUM (
--     'APROVADO', 'RECUSADO', 'APROVACAO_SOLICITADA', 'SALVO'
-- );

-- CREATE TYPE unificado.tipo_situacao_grupo AS ENUM (
--     'CERTIFICADO', 'CERTIFICADO_NAO_ATUALIZADO', 'EM_PREENCHIMENTO', 'AGUARDANDO_CERTIFICACAO', 'EXCLUIDO'
-- );

-- CREATE TYPE unificado.tipo_situacao_grupo_sigpesq AS ENUM (
--     'SALVO', 'RECUSADO', 'CERTIFICADO', 'EXCLUIDOCNPQ'
-- );

-- CREATE TYPE unificado.tipo_gerenciamento AS ENUM (
--     'REITORIA', 'INDEPENDENTE'
-- );

-- CREATE TYPE unificado.tipo_modalidade AS ENUM (
--     'VOLUNTARIO', 'BOLSISTA'
-- );

-- CREATE TYPE unificado.tipo_infraestrutura AS ENUM (
--     'EQUIPAMENTO', 'SOFTWARE'
-- );

-- ----------------------------------------------------------------------------
-- 2. Tabelas de Domínio com Carga Inicial (14 tabelas em SQLite)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tipo_formacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_formacao (nome) VALUES
('POS_DOUTORADO'), ('LIVRE_DOCENCIA'), ('DOUTORADO'), ('MESTRADO'),
('MESTRADO_PROFISSIONAL'), ('ESPECIALIZACAO'), ('APERFEICOAMENTO'),
('GRADUACAO'), ('CURSO_TECNICO_PROFISSIONALIZANTE'), ('ENSINO_MEDIO_2O_GRAU'),
('GRADUACAO_INTERROMPIDA'), ('MESTRADO_INTERROMPIDO'), ('ENSINO_MEDIO'), ('CURSO_TECNICO');

CREATE TABLE IF NOT EXISTS nivel_treinamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO nivel_treinamento (nome) VALUES
('POS_DOUTORADO'), ('DOUTORADO'), ('MESTRADO'), ('MESTRADO_PROFISSIONAL'),
('MBA'), ('ESPECIALIZACAO'), ('GRADUACAO'), ('ENSINO_PROFISSIONAL_TECNICO'),
('ENSINO_MEDIO_2O_GRAU'), ('ENSINO_FUNDAMENTAL');

CREATE TABLE IF NOT EXISTS natureza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO natureza (nome) VALUES
('Ensino'), ('Pesquisa'), ('Pós-Graduação'), ('Extensão'), ('Desenv. Institucional');

CREATE TABLE IF NOT EXISTS tipo_acao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_acao (nome) VALUES
('Programa'), ('Projeto'), ('Curso'), ('Evento'), ('Prestação de Serviço'), ('Produto'), ('Programa em Rede');

CREATE TABLE IF NOT EXISTS tipo_projeto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_projeto (nome) VALUES
('PESQUISA'), ('EXTENSAO'), ('DESENVOLVIMENTO');

CREATE TABLE IF NOT EXISTS programa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO programa (nome) VALUES
('pibic'), ('pibiti'), ('pibic_jr'), ('pibic_af'), ('finep'), ('propos'), ('piviti'),
('pivic'), ('pibic_em'), ('jtc'), ('picti');

CREATE TABLE IF NOT EXISTS tipo_apoio_financiamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_apoio_financiamento (nome) VALUES
('AUXILIO_FINANCEIRO'), ('BOLSA'), ('COOPERACAO'), ('REMUNERACAO'), ('OUTRA'), ('FINANCIAMENTO');

CREATE TABLE IF NOT EXISTS tipo_organizacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_organizacao (nome) VALUES
('Campus'), ('AgenciaFinanciamento'), ('ParceiroDemandante'), ('Instituicao'), ('InstituicaoParceira');

CREATE TABLE IF NOT EXISTS tipo_artigo_evento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_artigo_evento (nome) VALUES
('ARTIGO_PERIODICO'), ('TRABALHO_COMPLETO_CONGRESSO'), ('RESUMO_EXPANDIDO_CONGRESSO'), ('RESUMO_CONGRESSO'), ('OUTRO');

CREATE TABLE IF NOT EXISTS tipo_livro_capitulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_livro_capitulo (nome) VALUES
('LIVRO_PUBLICADO'), ('LIVRO_ORGANIZADO'), ('CAPITULO_LIVRO');

CREATE TABLE IF NOT EXISTS tipo_patente_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO tipo_patente_registro (nome) VALUES
('PATENTE'), ('PROGRAMA_COMPUTADOR'), ('DESENHO_INDUSTRIAL'), ('MARCA');

CREATE TABLE IF NOT EXISTS categoria_producao_tecnica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO categoria_producao_tecnica (nome) VALUES
('SOFTWARE_SEM_PATENTE'), ('TRABALHO_TECNICO'), ('PRODUCAO_ARTISTICA_CULTURAL'),
('CURSO_CURTA_DURACAO'), ('DESENVOLVIMENTO_MATERIAL_DIDATICO'), ('OUTRA');

CREATE TABLE IF NOT EXISTS vinculo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO vinculo (nome) VALUES
('Aluno'), ('Servidor'), ('Convidado');

CREATE TABLE IF NOT EXISTS situacao_participante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO situacao_participante (nome) VALUES
('Cursando'), ('Aprovado'), ('Reprovado');
