-- ============================================================================
-- 02_tabelas.sql: Definicao de Tabelas Principais, Herancas e Atributos (SQLite)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. ESTRUTURA ORGANIZACIONAL E LOCALIZACAO
-- ----------------------------------------------------------------------------

-- Classe Organizacao (Superclasse)
CREATE TABLE IF NOT EXISTS organizacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    id_tipo_organizacao INTEGER REFERENCES tipo_organizacao(id),
    id_organizacao_pai INTEGER REFERENCES organizacao(id)
);

-- Subclasse InstituicaoLattes -> Organizacao
CREATE TABLE IF NOT EXISTS instituicao_lattes (
    id INTEGER PRIMARY KEY REFERENCES organizacao(id) ON DELETE CASCADE,
    sigla TEXT,
    pais TEXT
);

-- Subclasse InstituicaoParceiraCNPQ -> Organizacao
CREATE TABLE IF NOT EXISTS instituicao_parceira_cnpq (
    id INTEGER PRIMARY KEY REFERENCES organizacao(id) ON DELETE CASCADE,
    sigla TEXT,
    uf TEXT
);

-- Classe Endereco
CREATE TABLE IF NOT EXISTS endereco (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logradouro TEXT,
    numero TEXT,
    complemento TEXT,
    bairro TEXT,
    localidade TEXT,
    uf TEXT,
    cep TEXT,
    caixa_postal TEXT,
    latitude TEXT,
    longitude TEXT
);

-- ----------------------------------------------------------------------------
-- 2. AREAS DE CONHECIMENTO E IDIOMAS
-- ----------------------------------------------------------------------------

-- Classe GrandeArea
CREATE TABLE IF NOT EXISTS grande_area (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe AreaConhecimento
CREATE TABLE IF NOT EXISTS area_conhecimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    id_grande_area INTEGER REFERENCES grande_area(id)
);

-- Classe SubareaConhecimentoLattes
CREATE TABLE IF NOT EXISTS subarea_conhecimento_lattes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    id_area_conhecimento INTEGER NOT NULL REFERENCES area_conhecimento(id)
);

-- Classe EspecialidadeLattes
CREATE TABLE IF NOT EXISTS especialidade_lattes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    id_subarea_conhecimento INTEGER NOT NULL REFERENCES subarea_conhecimento_lattes(id)
);

-- Classe Idioma
CREATE TABLE IF NOT EXISTS idioma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_idioma TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3. PESSOAS E HIERARQUIA DE PESSOAS
-- ----------------------------------------------------------------------------

-- Classe Titulacao (Declarada antes de pesquisador para FK direta)
CREATE TABLE IF NOT EXISTS titulacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe Curso (Declarada antes de estudante/formacao para FK direta)
CREATE TABLE IF NOT EXISTS curso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe Pessoa (Superclasse)
CREATE TABLE IF NOT EXISTS pessoa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Subclasse PessoaLattes -> Pessoa
CREATE TABLE IF NOT EXISTS pessoa_lattes (
    id INTEGER PRIMARY KEY REFERENCES pessoa(id) ON DELETE CASCADE,
    id_lattes TEXT,
    nome_citacoes TEXT,
    texto_resumo TEXT,
    bolsa_produtividade TEXT,
    endereco_profissional TEXT,
    url_lattes TEXT,
    data_atualizacao_cv TEXT
);

-- Subclasse PessoaSRC -> Pessoa
CREATE TABLE IF NOT EXISTS pessoa_src (
    id INTEGER PRIMARY KEY REFERENCES pessoa(id) ON DELETE CASCADE
);

-- Classe AreaAtuacao (ligada a GrandeArea [1], PessoaLattes [1])
CREATE TABLE IF NOT EXISTS area_atuacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT,
    subarea TEXT,
    especialidade TEXT,
    id_grande_area INTEGER NOT NULL REFERENCES grande_area(id),
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE
);

-- Subclasse Pesquisador -> Pessoa
CREATE TABLE IF NOT EXISTS pesquisador (
    id INTEGER PRIMARY KEY REFERENCES pessoa(id) ON DELETE CASCADE,
    id_titulacao INTEGER REFERENCES titulacao(id),
    id_organizacao INTEGER REFERENCES organizacao(id)
);

-- Subclasse Estudante -> Pessoa
CREATE TABLE IF NOT EXISTS estudante (
    id INTEGER PRIMARY KEY REFERENCES pessoa(id) ON DELETE CASCADE,
    id_campus INTEGER REFERENCES organizacao(id),
    id_nivel_treinamento INTEGER REFERENCES nivel_treinamento(id),
    id_curso INTEGER REFERENCES curso(id)
);

-- ----------------------------------------------------------------------------
-- 4. GRUPOS DE PESQUISA, LINHAS E INFRAESTRUTURA
-- ----------------------------------------------------------------------------

-- Classe GrupoPesquisa (Superclasse)
CREATE TABLE IF NOT EXISTS grupo_pesquisa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    sigla TEXT,
    url_cnpq TEXT,
    id_organizacao INTEGER NOT NULL REFERENCES organizacao(id),
    id_area_conhecimento INTEGER NOT NULL REFERENCES area_conhecimento(id)
);

-- Subclasse GrupoPesquisaCNPQ -> GrupoPesquisa
CREATE TABLE IF NOT EXISTS grupo_pesquisa_cnpq (
    id INTEGER PRIMARY KEY REFERENCES grupo_pesquisa(id) ON DELETE CASCADE,
    situacao_grupo TEXT,
    ano_formacao INTEGER,
    data_situacao TEXT,
    data_ultimo_envio TEXT,
    repercussoes TEXT,
    id_endereco INTEGER REFERENCES endereco(id),
    id_instituicao INTEGER NOT NULL REFERENCES organizacao(id),
    id_campus INTEGER NOT NULL REFERENCES organizacao(id)
);

-- Classe GrupoPesquisaExterno
CREATE TABLE IF NOT EXISTS grupo_pesquisa_externo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe LinhaPesquisa
CREATE TABLE IF NOT EXISTS linha_pesquisa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL
);

-- Classe EquipamentoSoftware
CREATE TABLE IF NOT EXISTS equipamento_software (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT
);

-- Comunicacoes do GrupoPesquisaCNPQ
CREATE TABLE IF NOT EXISTS telefone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fax (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS website (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE
);

-- Email de contato do GrupoPesquisaCNPQ (e-mail de pessoa não é guardado: LGPD)
CREATE TABLE IF NOT EXISTS email (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endereco TEXT NOT NULL,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 5. MEMBROS DE GRUPO
-- ----------------------------------------------------------------------------

-- Classe Papel
CREATE TABLE IF NOT EXISTS papel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe MembroGrupo (Superclasse)
CREATE TABLE IF NOT EXISTS membro_grupo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_inicio TEXT,
    data_fim TEXT,
    id_papel INTEGER REFERENCES papel(id)
);

-- Subclasse MembroGrupoCNPQ -> MembroGrupo
CREATE TABLE IF NOT EXISTS membro_grupo_cnpq (
    id INTEGER PRIMARY KEY REFERENCES membro_grupo(id) ON DELETE CASCADE,
    status_participacao TEXT,
    id_pessoa INTEGER NOT NULL REFERENCES pessoa(id) ON DELETE CASCADE,
    id_grupo_pesquisa_cnpq INTEGER NOT NULL REFERENCES grupo_pesquisa_cnpq(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 6. INICIATIVAS, ACOES, PROJETOS E ATIVIDADES
-- ----------------------------------------------------------------------------

-- Classe Iniciativa (Superclasse)
CREATE TABLE IF NOT EXISTS iniciativa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Subclasse Acao -> Iniciativa
CREATE TABLE IF NOT EXISTS acao (
    id INTEGER PRIMARY KEY REFERENCES iniciativa(id) ON DELETE CASCADE,
    id_origem INTEGER, -- ID original do SRC
    processo TEXT,
    data_cadastro TEXT,
    relatorio_aprovado INTEGER,
    url_detalhe TEXT,
    id_natureza INTEGER REFERENCES natureza(id),
    id_tipo_acao INTEGER REFERENCES tipo_acao(id),
    id_acao_pai INTEGER REFERENCES acao(id),
    id_area_conhecimento INTEGER REFERENCES area_conhecimento(id),
    id_coordenador INTEGER REFERENCES pessoa(id)
);

-- Classe TipoAtividade
CREATE TABLE IF NOT EXISTS tipo_atividade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL
);

-- Classe Atividade (Composicao com Acao: Acao ◆ Atividade)
CREATE TABLE IF NOT EXISTS atividade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    id_acao INTEGER NOT NULL REFERENCES acao(id) ON DELETE CASCADE,
    id_tipo_atividade INTEGER REFERENCES tipo_atividade(id)
);

-- Subclasse MembroEquipeExecucaoSRC -> MembroGrupo
CREATE TABLE IF NOT EXISTS membro_equipe_execucao_src (
    id INTEGER PRIMARY KEY REFERENCES membro_grupo(id) ON DELETE CASCADE,
    id_atividade INTEGER NOT NULL REFERENCES atividade(id) ON DELETE CASCADE,
    id_pessoa INTEGER NOT NULL REFERENCES pessoa(id) ON DELETE CASCADE,
    id_vinculo INTEGER REFERENCES vinculo(id)
);

-- Classe RegistroParticipante
CREATE TABLE IF NOT EXISTS registro_participante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_horaria REAL,
    certificado INTEGER,
    data_inicio TEXT,
    data_termino TEXT,
    id_atividade INTEGER NOT NULL REFERENCES atividade(id) ON DELETE CASCADE,
    id_pessoa INTEGER NOT NULL REFERENCES pessoa(id) ON DELETE CASCADE,
    id_situacao INTEGER REFERENCES situacao_participante(id)
);

-- Subclasse ProjetoPesquisa -> Iniciativa
CREATE TABLE IF NOT EXISTS projeto_pesquisa (
    id INTEGER PRIMARY KEY REFERENCES iniciativa(id) ON DELETE CASCADE,
    id_origem INTEGER, -- ID original do SigPesq
    data_inicio TEXT,
    data_fim TEXT,
    palavras_chave TEXT,
    sigilo INTEGER,
    id_natureza_projeto TEXT,
    parecer_diretoria TEXT,
    id_campus INTEGER REFERENCES organizacao(id),
    id_area_conhecimento INTEGER REFERENCES area_conhecimento(id),
    id_coordenador INTEGER REFERENCES pesquisador(id)
);

-- Subclasse ProjetoLATTES -> Iniciativa
CREATE TABLE IF NOT EXISTS projeto_lattes (
    id INTEGER PRIMARY KEY REFERENCES iniciativa(id) ON DELETE CASCADE,
    ano_inicio INTEGER,
    ano_conclusao INTEGER,
    situacao TEXT,
    descricao TEXT
);

-- Classe Edital
CREATE TABLE IF NOT EXISTS edital (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL
);

-- Classe PlanoTrabalho
CREATE TABLE IF NOT EXISTS plano_trabalho (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo INTEGER,
    titulo TEXT NOT NULL,
    id_projeto_pesquisa INTEGER NOT NULL REFERENCES projeto_pesquisa(id) ON DELETE CASCADE,
    id_edital INTEGER REFERENCES edital(id),
    id_area_conhecimento INTEGER REFERENCES area_conhecimento(id)
);

-- Classe Orientacao
CREATE TABLE IF NOT EXISTS orientacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_origem INTEGER, -- ID original do SigPesq
    ano INTEGER,
    valor_bolsa REAL,
    data_inicio TEXT,
    data_fim TEXT,
    cancelado INTEGER,
    nome_cancelador TEXT,
    data_cancelado TEXT,
    relatorio_enviado INTEGER,
    modalidade TEXT,
    gerenciamento TEXT,
    id_programa INTEGER REFERENCES programa(id),
    id_plano_trabalho INTEGER NOT NULL REFERENCES plano_trabalho(id) ON DELETE CASCADE,
    id_orientador INTEGER NOT NULL REFERENCES pesquisador(id),
    id_orientado INTEGER NOT NULL REFERENCES estudante(id),
    id_campus INTEGER REFERENCES organizacao(id),
    id_financiador INTEGER REFERENCES organizacao(id)
);

-- ----------------------------------------------------------------------------
-- 7. VIDA ACADEMICA LATTES: FORMACOES, ATUACOES E ORIENTACOES LATTES
-- ----------------------------------------------------------------------------

-- Classe FormacaoAcademica
CREATE TABLE IF NOT EXISTS formacao_academica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tipo_formacao INTEGER REFERENCES tipo_formacao(id),
    ano_inicio INTEGER,
    ano_conclusao INTEGER,
    titulo_trabalho TEXT,
    descricao TEXT,
    nome_orientador TEXT,
    nome_coorientador TEXT,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_instituicao INTEGER NOT NULL REFERENCES instituicao_lattes(id),
    id_curso INTEGER REFERENCES curso(id)
);

-- Classe AtuacaoProfissional
CREATE TABLE IF NOT EXISTS atuacao_profissional (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ano_inicio INTEGER,
    ano_fim INTEGER,
    atual INTEGER,
    vinculo TEXT,
    enquadramento TEXT,
    regime_trabalho TEXT,
    atividades TEXT,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_instituicao INTEGER NOT NULL REFERENCES instituicao_lattes(id)
);

-- Classe OrientacaoLattes
CREATE TABLE IF NOT EXISTS orientacao_lattes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    modalidade TEXT,
    papel_orientacao TEXT,
    status TEXT,
    ano_inicio INTEGER,
    ano_conclusao INTEGER,
    tipo_trabalho TEXT,
    id_orientador INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE,
    id_orientando INTEGER REFERENCES pessoa_lattes(id),
    id_instituicao INTEGER NOT NULL REFERENCES organizacao(id),
    id_financiador INTEGER REFERENCES organizacao(id)
);

-- Classe BancaExaminadora
CREATE TABLE IF NOT EXISTS banca_examinadora (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modalidade TEXT,
    titulo_trabalho TEXT,
    ano INTEGER,
    curso TEXT,
    descricao TEXT,
    id_instituicao INTEGER REFERENCES organizacao(id),
    id_candidato INTEGER NOT NULL REFERENCES pessoa_lattes(id)
);

-- Classe EventoCientifico
CREATE TABLE IF NOT EXISTS evento_cientifico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_evento TEXT NOT NULL,
    natureza_tipo_evento TEXT,
    ano INTEGER
);

-- ----------------------------------------------------------------------------
-- 8. PRODUCAO CIENTIFICA E HIERARQUIA DE PRODUCOES
-- ----------------------------------------------------------------------------

-- Classe Producao (Superclasse)
CREATE TABLE IF NOT EXISTS producao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    ano INTEGER
);

-- Subclasse ArtigoTrabalhoEvento -> Producao
CREATE TABLE IF NOT EXISTS artigo_trabalho_evento (
    id INTEGER PRIMARY KEY REFERENCES producao(id) ON DELETE CASCADE,
    id_tipo_publicacao INTEGER REFERENCES tipo_artigo_evento(id),
    veiculo_revista_evento TEXT,
    doi TEXT,
    issn_isbn TEXT,
    volume TEXT,
    numero TEXT,
    paginas TEXT,
    data_publicacao TEXT,
    natureza TEXT
);

-- Subclasse LivroCapitulo -> Producao
CREATE TABLE IF NOT EXISTS livro_capitulo (
    id INTEGER PRIMARY KEY REFERENCES producao(id) ON DELETE CASCADE,
    id_tipo_livro_capitulo INTEGER REFERENCES tipo_livro_capitulo(id),
    editora TEXT,
    paginas TEXT
);

-- Subclasse ProducaoTecnicaArtisticaBibliografica -> Producao
CREATE TABLE IF NOT EXISTS producao_tecnica_artistica_bibliografica (
    id INTEGER PRIMARY KEY REFERENCES producao(id) ON DELETE CASCADE,
    id_categoria INTEGER REFERENCES categoria_producao_tecnica(id),
    subtipo TEXT
);

-- Subclasse PatenteRegistro -> Producao
-- id_instituicao_depositante e anulavel conforme especificacao P5 (patentes Lattes nem sempre tem depositante)
CREATE TABLE IF NOT EXISTS patente_registro (
    id INTEGER PRIMARY KEY REFERENCES producao(id) ON DELETE CASCADE,
    id_tipo_patente_registro INTEGER REFERENCES tipo_patente_registro(id),
    modalidade_patente TEXT,
    pais TEXT,
    data_registro TEXT,
    codigo_registro TEXT,
    id_instituicao_depositante INTEGER REFERENCES organizacao(id)
);

-- Classe PremioTitulo
CREATE TABLE IF NOT EXISTS premio_titulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao_titulo TEXT NOT NULL,
    ano INTEGER,
    id_pessoa_lattes INTEGER NOT NULL REFERENCES pessoa_lattes(id) ON DELETE CASCADE
);
