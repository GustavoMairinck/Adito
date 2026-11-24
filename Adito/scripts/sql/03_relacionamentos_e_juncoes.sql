-- ============================================================================
-- 03_relacionamentos_e_juncoes.sql: Classes de Associacao e Tabelas de Juncao (SQLite)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CLASSES DE ASSOCIACAO E ASSOCIATIVE DO MODELO (Possuem ID proprio)
-- ----------------------------------------------------------------------------

-- Classe de Associacao: ParceriaGrupo (GrupoPesquisaCNPQ 1..* -- 1..* InstituicaoParceiraCNPQ)
CREATE TABLE IF NOT EXISTS parceria_grupo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE,
    id_instituicao_parceira INTEGER NOT NULL REFERENCES instituicao_parceira_cnpq(id) ON DELETE CASCADE,
    tipo TEXT
);

-- Classe de Associacao: MembroProjeto (PessoaLattes 0..* -- 0..* ProjetoLATTES)
CREATE TABLE IF NOT EXISTS membro_projeto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_projeto_lattes INTEGER NOT NULL REFERENCES projeto_lattes(id) ON DELETE CASCADE,
    papel TEXT
);

-- Classe de Associacao: FomentoProjeto (Organizacao fomento 0..* -- 0..* ProjetoLATTES)
CREATE TABLE IF NOT EXISTS fomento_projeto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_organizacao INTEGER NOT NULL REFERENCES organizacao(id) ON DELETE CASCADE,
    id_projeto_lattes INTEGER NOT NULL REFERENCES projeto_lattes(id) ON DELETE CASCADE,
    id_tipo_apoio INTEGER REFERENCES tipo_apoio_financiamento(id)
);

-- Classe <<associative>>: ParticipacaoEvento (PessoaLattes 1 -- 1..* EventoCientifico)
CREATE TABLE IF NOT EXISTS participacao_evento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_evento_cientifico INTEGER NOT NULL REFERENCES evento_cientifico(id) ON DELETE CASCADE,
    papel_evento TEXT,
    titulo_apresentacao TEXT
);

-- Classe <<associative>>: ProficienciaIdioma (PessoaLattes 1 -- 0..* Idioma)
CREATE TABLE IF NOT EXISTS proficiencia_idioma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_idioma INTEGER NOT NULL REFERENCES idioma(id) ON DELETE CASCADE,
    compreende TEXT,
    fala TEXT,
    le TEXT,
    escreve TEXT
);

-- ----------------------------------------------------------------------------
-- 2. TABELAS DE JUNCAO PURAS N:N (Sem ID proprio, PK composta por FKs)
-- ----------------------------------------------------------------------------

-- A04: PessoaLattes [0..*] -- Titulacao [0..*]
CREATE TABLE IF NOT EXISTS pessoa_lattes_titulacao (
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_titulacao INTEGER NOT NULL REFERENCES titulacao(id) ON DELETE CASCADE,
    PRIMARY KEY (id_pessoa_lattes, id_titulacao)
);

-- A07: GrupoPesquisa [1..*] -- Pesquisador [1..*] (lider)
CREATE TABLE IF NOT EXISTS lideranca_grupo_pesquisa (
    id_grupo_pesquisa INTEGER NOT NULL REFERENCES grupo_pesquisa(id) ON DELETE CASCADE,
    id_pesquisador INTEGER NOT NULL REFERENCES pesquisador(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa, id_pesquisador)
);

-- A13: GrupoPesquisaCNPQ [0..*] -- GrandeArea [0..*]
CREATE TABLE IF NOT EXISTS grupo_pesquisa_grande_area (
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE,
    id_grande_area INTEGER NOT NULL REFERENCES grande_area(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa_cnpq, id_grande_area)
);

-- A38: GrupoPesquisaExterno [0..*] -- ProjetoPesquisa [1..*] (coopera em)
CREATE TABLE IF NOT EXISTS cooperacao_grupo_externo_projeto (
    id_grupo_pesquisa_externo INTEGER NOT NULL REFERENCES grupo_pesquisa_externo(id) ON DELETE CASCADE,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa_externo, id_projeto_pesquisa)
);

-- A42: Organizacao (fomento) [0..*] -- Acao [0..*] (financia)
CREATE TABLE IF NOT EXISTS fomento_acao (
    id_organizacao INTEGER NOT NULL REFERENCES organizacao(id) ON DELETE CASCADE,
    id_acao INTEGER NOT NULL REFERENCES acao(id) ON DELETE CASCADE,
    PRIMARY KEY (id_organizacao, id_acao)
);

-- A43: Organizacao (campus) [1..*] -- Acao [0..*] (possui)
CREATE TABLE IF NOT EXISTS acao_campus (
    id_organizacao INTEGER NOT NULL REFERENCES organizacao(id) ON DELETE CASCADE,
    id_acao INTEGER NOT NULL REFERENCES acao(id) ON DELETE CASCADE,
    PRIMARY KEY (id_organizacao, id_acao)
);

-- A49: Organizacao (parceiro demandante) [0..*] -- ProjetoPesquisa [1..*] (demanda)
CREATE TABLE IF NOT EXISTS parceiro_demandante_projeto (
    id_organizacao INTEGER NOT NULL REFERENCES organizacao(id) ON DELETE CASCADE,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_organizacao, id_projeto_pesquisa)
);

-- A52: Estudante [0..*] -- ProjetoPesquisa [0..*] (participa)
CREATE TABLE IF NOT EXISTS participacao_estudante_projeto (
    id_estudante INTEGER NOT NULL REFERENCES estudante(id) ON DELETE CASCADE,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_estudante, id_projeto_pesquisa)
);

-- A69: PessoaLattes (autor) [1..*] -- Producao [0..*] (autor de)
CREATE TABLE IF NOT EXISTS autoria_producao (
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_producao INTEGER NOT NULL REFERENCES producao(id) ON DELETE CASCADE,
    PRIMARY KEY (id_pessoa_lattes, id_producao)
);

-- A73: Pesquisador [1..*] -- ProjetoPesquisa [0..*] (participa)
CREATE TABLE IF NOT EXISTS participacao_pesquisador_projeto (
    id_pesquisador INTEGER NOT NULL REFERENCES pesquisador(id) ON DELETE CASCADE,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_pesquisador, id_projeto_pesquisa)
);

-- A78: BancaExaminadora [0..*] -- PessoaLattes [1..*] (membros avaliadores da banca)
CREATE TABLE IF NOT EXISTS membro_banca_examinadora (
    id_banca_examinadora INTEGER NOT NULL REFERENCES banca_examinadora(id) ON DELETE CASCADE,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    PRIMARY KEY (id_banca_examinadora, id_pessoa_lattes)
);

-- A85: GrupoPesquisa [0..*] -- ProjetoPesquisa [0..*] (atua em)
CREATE TABLE IF NOT EXISTS grupo_pesquisa_projeto (
    id_grupo_pesquisa INTEGER NOT NULL REFERENCES grupo_pesquisa(id) ON DELETE CASCADE,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa, id_projeto_pesquisa)
);

-- A87: GrupoPesquisaCNPQ [1] -- EquipamentoSoftware [0..*] (tem acesso a)
CREATE TABLE IF NOT EXISTS grupo_pesquisa_equipamento (
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE,
    id_equipamento_software INTEGER NOT NULL REFERENCES equipamento_software(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa_cnpq, id_equipamento_software)
);

-- A88: GrupoPesquisaCNPQ [1..*] -- LinhaPesquisa [0..*] (pesquisa em)
CREATE TABLE IF NOT EXISTS grupo_pesquisa_linha_pesquisa (
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE,
    id_linha_pesquisa INTEGER NOT NULL REFERENCES linha_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_grupo_pesquisa_cnpq, id_linha_pesquisa)
);

-- A89: PessoaLattes [1..*] -- LinhaPesquisa [0..*] (pesquisa em)
CREATE TABLE IF NOT EXISTS pesquisador_linha_pesquisa (
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_linha_pesquisa INTEGER NOT NULL REFERENCES linha_pesquisa(id) ON DELETE CASCADE,
    PRIMARY KEY (id_pessoa_lattes, id_linha_pesquisa)
);

-- ----------------------------------------------------------------------------
-- 3. INDICES PARA PERFORMANCE DE CHAVES ESTRANGEIRAS
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_area_conhecimento_grande_area ON area_conhecimento(id_grande_area);
CREATE INDEX IF NOT EXISTS idx_subarea_area_conhecimento ON subarea_conhecimento_lattes(id_area_conhecimento);
CREATE INDEX IF NOT EXISTS idx_especialidade_subarea ON especialidade_lattes(id_subarea_conhecimento);
CREATE INDEX IF NOT EXISTS idx_area_atuacao_grande_area ON area_atuacao(id_grande_area);
CREATE INDEX IF NOT EXISTS idx_area_atuacao_pessoa ON area_atuacao(id_pessoa_lattes);
CREATE INDEX IF NOT EXISTS idx_pesquisador_titulacao ON pesquisador(id_titulacao);
CREATE INDEX IF NOT EXISTS idx_estudante_curso ON estudante(id_curso);
CREATE INDEX IF NOT EXISTS idx_grupo_pesquisa_org ON grupo_pesquisa(id_organizacao);
CREATE INDEX IF NOT EXISTS idx_acao_coordenador ON acao(id_coordenador);
CREATE INDEX IF NOT EXISTS idx_atividade_acao ON atividade(id_acao);
CREATE INDEX IF NOT EXISTS idx_projeto_pesquisa_coord ON projeto_pesquisa(id_coordenador);
CREATE INDEX IF NOT EXISTS idx_plano_trabalho_projeto ON plano_trabalho(id_projeto_pesquisa);
CREATE INDEX IF NOT EXISTS idx_orientacao_plano ON orientacao(id_plano_trabalho);
CREATE INDEX IF NOT EXISTS idx_orientacao_orientador ON orientacao(id_orientador);
CREATE INDEX IF NOT EXISTS idx_orientacao_orientado ON orientacao(id_orientado);
CREATE INDEX IF NOT EXISTS idx_orientacao_lattes_orientador ON orientacao_lattes(id_orientador);
CREATE INDEX IF NOT EXISTS idx_orientacao_lattes_orientando ON orientacao_lattes(id_orientando);
CREATE INDEX IF NOT EXISTS idx_banca_candidato ON banca_examinadora(id_candidato);
CREATE INDEX IF NOT EXISTS idx_premio_pessoa ON premio_titulo(id_pessoa_lattes);
