# Relatório Técnico: Adaptação do Adito para DuckDB OLAP e Criação das Views Fato

**Data:** 13/11/2026
**Iniciativa:** Adito — Oráculo Local do IFES (Campus Serra)
**Story Relacionada:** `US-ADITO-DUCKDB-01` (`EPIC-07`)
**Branch:** `feat/adito-duckdb-olap`

---

## 1. Contexto e Motivação

O **Adito** (Oráculo ESX) foi concebido originalmente com duas bases SQLite: `app.db` (para uso operacional do Django) e `dados.db` (com dados demonstrativos de `exemplo-vendas`). Em paralelo, o pipeline de ETL unificava os dados de Pesquisa e Extensão do IFES Campus Serra (oriundos de 4 fontes: **SRC**, **SigPesq**, **Lattes** e **CNPq/DGP**) em um banco PostgreSQL unificado com 41 tabelas normalizadas.

Para transformar o Adito em um assistente analítico desktop leve, 100% offline, seguro e de alta velocidade para os gestores, definiu-se a migração da camada analítica para **DuckDB OLAP** em formato colunar, materializando as **6 tabelas fato** consolidadas (especificadas em `Docs/Fatos/PropostaFatos.md`) e eliminando qualquer necessidade de servidor PostgreSQL externo.

---

## 2. Arquitetura de Bancos de Dados

O aplicativo adota a separação estrita de responsabilidades entre operações transacionais e analíticas:

```
┌─────────────────────────────────────────────────────────────┐
│                    Oráculo ESX (Adito)                      │
├──────────────────────────────┬──────────────────────────────┤
│       app.db (SQLite)        │    dados.duckdb (DuckDB)     │
│   Transacional / Operacional │     Analítico / OLAP Fatos   │
├──────────────────────────────┼──────────────────────────────┤
│ • Usuários locais e Tenant   │ • Formato colunar em disco   │
│ • Conversas e Mensagens      │ • 41 tabelas brutas unificado│
│ • Histórico de Execuções SQL │ • 6 tabelas fato em main     │
│ • Definições de Contextos    │ • Aberto estritamente        │
│ • Checkpoints do LangGraph   │   somente-leitura (read-only)│
│ • Embeddings e Cache FTS5    │ • Protegido por ReadPolicy   │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Geração da Base Analítica (`Adito/scripts/gerar_duckdb.py`)

O script automatizado lê os 41 arquivos JSON exportados e o `manifesto.json` localizados em `Adito/etl/saida/json/` e constrói o banco `Adito/app/data/dados.duckdb`:

1. **Carga Colunar das 41 Tabelas Base:**Em vez de inserções linha a linha, utiliza a função nativa `read_json(..., format='array', columns={...})` do DuckDB, importando todas as tabelas para o schema `unificado.<tabela>` em aproximadamente 2,5 segundos.
2. **Validação de Integridade:**Confronta a contagem de linhas (`row_count`) e integridade de cada tabela contra o `manifesto.json`.
3. **Materialização das 6 Tabelas Fato:**Executa os scripts DDL analíticos de resolução de entidades gerando tabelas físicas colunares no schema `main` (e views espelho em `unificado` para compatibilidade).
4. **Otimização de Armazenamento:**
   Executa `CHECKPOINT`, `PRAGMA vacuum` e `PRAGMA optimize`.

### As 6 Tabelas Fato Materializadas

| Tabela Fato (`main.vfact_*_resolved`)  | Base Principal       | Descrição Analítica                                                                                                  | Total de Registros |
| ---------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------- | :----------------: |
| `vfact_extensao_acao_resolved`         | **SRC**        | Ações de extensão com tipo, modalidade, campus, público, financiamento e coordenador resolvido por nome normalizado |   **207**   |
| `vfact_extensao_participacao_resolved` | **SRC**        | Participações de pessoas em extensão (discentes, docentes, membros externos) com vínculo e carga horária           |  **6.741**  |
| `vfact_projeto_pesquisa_resolved`      | **SigPesq**    | Projetos de pesquisa aprovados com campus, parecer, natureza (básica/aplicada), grande área e coordenador             |   **236**   |
| `vfact_orientacao_bolsa_resolved`      | **SigPesq**    | Bolsas e orientações com ano, discente, orientador, agência financiadora, programa e valor de investimento           |  **1.203**  |
| `vfact_producao_cientifica_resolved`   | **Lattes**     | Produções científicas e intelectuais (artigos, livros, softwares, patentes) com ano, autor e grande área            |  **1.232**  |
| `vfact_grupo_pesquisa_membro_resolved` | **CNPq / DGP** | Membros e líderes de grupos de pesquisa certificados pelo CNPq no IFES com campus e área                              |   **553**   |

---

## 4. Adaptações no Backend Django (`Adito/app/backend/api/`)

Todas as camadas do backend foram convertidas de SQLite para DuckDB para o banco de dados analítico:

### 4.1. Camada de Dados (`core/datastore.py`)

- **`dados_db_path()`**: Atualizado para localizar `dados.duckdb` na pasta de dados do app (`XDG_DATA_HOME` / `%LOCALAPPDATA%`) ou no fallback do repositório (`Adito/app/data/dados.duckdb`).
- **`connect_dados(policy)`**: Abre conexão DuckDB com flag `read_only=True` e defesa em profundidade nativa do DuckDB: `enable_external_access=False` (bloqueia nativamente a leitura de arquivos locais e URLs pelo banco) e `lock_configuration=True` (impede comandos SQL de religarem a opção).
- **Wrappers de Compatibilidade**: Implementadas as classes `DadosConnection`, `DadosCursor` e `DadosRow`, provendo acesso indexado por nome de coluna (`row["coluna"]`), conversão para dicionário (`dict(row)`) e compatibilidade total com o ecossistema Django/LangChain existente.

### 4.2. Segurança SQL e Proteção LGPD (`agents/bi_agent/sql_security.py`)

- **Dialeto DuckDB**: Transição do parser AST `sqlglot` de dialeto `sqlite` para `duckdb`.
- **Whitelist Estrita**: Bloqueia acesso a qualquer tabela que não seja uma das 6 tabelas fato autorizadas pelo contexto ativo (`exposed_views`).
- **Bloqueio de Funções de Sistema e I/O**: Bloqueia chamadas potencialmente perigosas como `read_csv`, `read_parquet`, `read_json`, `parquet_scan`, `glob`, `copy`, `attach`, `install`, `load`, `pragma`, `call`, `set`.
- **Proteção LGPD**: Impede seleção de colunas sensíveis (como `cpf` e `email`) declaradas na política de leitura ou no esquema.

### 4.3. Motor de Contextos e Regras (`core/contexts.py`)

- **`BASE_SQL_RULES`**: Prompt base reescrito com as diretrizes do dialeto DuckDB OLAP: suporte a `ILIKE` (busca textual sem case sensitive), `EXTRACT(YEAR FROM col)`, `CAST(x AS TYPE)` ou operador `::`, agregações `COUNT(DISTINCT ...)`, `COALESCE` e regras de `LIMIT`.
- **Introspecção via `DESCRIBE`**: A função `view_columns()` foi adaptada para rodar `DESCRIBE "{view}"` no DuckDB em vez do antigo `PRAGMA table_info` do SQLite.
- **Sincronização de Contextos (`sync_default_contexts`)**: Unifica os contextos padrão da aplicação com contextos customizados do usuário, desativando automaticamente no banco operacional (`app.db`) qualquer contexto legado cujas views não existam no `dados.duckdb`.

### 4.4. Agente de BI e LangGraph

- **`nodes/sql_validator.py`**: Validação com CTE e schema DuckDB.
- **`nodes/sql_generator.py` e `nodes/sql_corrector.py`**: Geração orientada a OLAP DuckDB, orientando a LLM sobre operadores analíticos e tabelas materializadas.
- **`analytics_index/services.py`**: Introspecção de metadados adaptada para `information_schema.tables`.

---

## 5. Criação do Contexto `pesquisa-extensao-ifes`

Criada a estrutura em `Adito/app/contexts/pesquisa-extensao-ifes/`:

- **`views.json`**: Declara as 6 tabelas fato, descrevendo detalhadamente a finalidade de cada coluna e definindo colunas de busca textual e mascaramento LGPD.
- **`rules.md`**: Regras de negócio institucionais do IFES, definições das 4 fontes de dados, métricas financeiras estimadas para bolsas e diretrizes de cálculo analítico.
- **`examples.json`**: 16 exemplos validados de perguntas em linguagem natural pareadas com consultas SQL otimizadas em DuckDB, incluindo:
  - Perguntas isoladas para cada uma das fontes (SRC, SigPesq, Lattes, CNPq).
  - Consultas analíticas avançadas cruzando as 4 bases simultaneamente (panorama unificado, pesquisadores atuantes nas 4 bases, evolução temporal anual e cruzamento por grande área do conhecimento).
- O contexto anterior `exemplo-vendas` foi desativado com `"ativo": false`.

---

## 6. Integração do Google Gemini como LLM Oficial

Substituição da chave e bibliotecas da Mistral pelo ecossistema **Google Gemini**:

- **Biblioteca**: `langchain-google-genai` com `google-genai` v2+.
- **Modelos**:
  - LLM de Roteamento, Geração de SQL e Chat: `gemini-3.5-flash` (adotado após validação em produção devido à descontinuação do `gemini-2.5-flash` pelo Google para novas chaves).
  - Embeddings: `models/gemini-embedding-001`.
- **Cofre de Chaves do SO (Tauri)**:
  - O cofre desktop (`keyring`) foi atualizado para gerenciar `gemini-api-key`, injetando `GEMINI_API_KEY` e `GOOGLE_API_KEY` no ambiente do backend.
- **Interface Gráfica (Vue 3)**:
  - Telas de **Configurações** e **Administração** adaptadas com badges, validação de status e orientações específicas para chaves da Google AI Studio.

---

## 7. Verificação e Testes

- **Suíte de Testes Automatizados**:
  - `python manage.py test core`: 8/8 testes executados com sucesso (verificando conexão DuckDB somente-leitura, validação de views, bloqueios de segurança SQL e introspecção de esquema).
- **Validação de Performance**:
  - Carga e materialização completa das 6 tabelas fato: **~2,5 segundos**.
  - Tamanho final do arquivo `dados.duckdb`: **~8,8 MB** (compressão colunar nativa).
- **Validação Funcional Desktop**:
  - Subida ponta a ponta pelo script `./rodar_desktop.sh` com Vite + Tauri + Backend Django Daphne.

---

## 8. Como Executar

Para reproduzir o banco e iniciar o aplicativo:

```bash
# 1. Gerar o banco DuckDB analítico com as 6 tabelas fato
python Adito/scripts/gerar_duckdb.py

# 2. Executar os testes automatizados do núcleo
python Adito/app/backend/api/manage.py test core

# 3. Subir o aplicativo desktop completo (Vite + Tauri + Backend)
bash ./rodar_desktop.sh
```
