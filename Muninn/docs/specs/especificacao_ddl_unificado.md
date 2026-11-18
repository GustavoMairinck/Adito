# Especificação Técnica: Mapeamento Objeto-Relacional do Modelo Unificado (100% SQLite)

**Status:** Aprovado  
**Data da Revisão Final:** 18/11/2026  
**Fonte Original:** `Docs/ModelosClasses/ModeloClassesUnificado.asta` (Diagrama `ModeloCore_SRC_DGP_SIGPESQ_LATTES`)  
**Banco Alvo:** SQLite 3 nativo (`Adito/app/data/dados.db`), 100% OLTP como Single Source of Truth

---

## 1. Visão Geral das Decisões de Arquitetura

1. **Diagrama Canônico:** Apenas o diagrama unificado final (`ModeloCore_SRC_DGP_SIGPESQ_LATTES`) foi considerado como fonte canônica.
2. **Arquitetura 100% SQLite (dados.db):**
   * Eliminação total de Docker, PostgreSQL e DuckDB (`dados.duckdb`).
   * **42 Tabelas Base** em 3ª Forma Normal (3FN), com integridade referencial estrita (`PRAGMA foreign_keys = ON`).
   * **6 Tabelas Fato Analíticas** modeladas como **VIEWs relacionais dinâmicas (`vfact_*_resolved`)**, calculadas em tempo real sobre as tabelas base sem duplicação física em disco.
3. **Estratégia de Herança (Tabela por Subclasse / Joined-Table):**
   * A superclasse define a chave primária `id INTEGER PRIMARY KEY`.
   * As subclasses possuem a chave primária `id INTEGER PRIMARY KEY REFERENCES superclasse(id) ON DELETE CASCADE`.
   * Permite que a mesma entidade base (ex: `pessoa`) possua múltiplos papéis/extensões (`pessoa_lattes`, `pesquisador`, `estudante`).
4. **Estratégia Híbrida de Tipos e Domínios:**
   * **14 Tabelas de Domínio:** Usadas para taxonomias acadêmicas e operacionais que podem expandir (`tipo_formacao`, `nivel_treinamento`, `tipo_acao`, `programa`, etc.), com `id INTEGER PRIMARY KEY AUTOINCREMENT`.
   * Domínios ampliados para acomodar todas as fontes: programas `pivic`, `pibic_em`, `jtc`, `picti`, status `EXCLUIDO`, escolaridade `ENSINO_FUNDAMENTAL` e natureza `FINANCIAMENTO`.
5. **Tipos de Dados SQLite:**
   * Textos: `TEXT` para todos os atributos textuais.
   * Datas: `TEXT` no padrão ISO-8601 (`YYYY-MM-DD`).
   * Chaves e Flags: `INTEGER` (`0` ou `1` para booleanos).
   * Valores Monetários: `REAL`.
6. **Defesa em Profundidade para Leitura:**
   * Acesso núcleo via `file:dados.db?mode=ro` com `PRAGMA query_only = ON`.
   * `set_authorizer` bloqueando qualquer comando DML/DDL (`INSERT`, `UPDATE`, `DELETE`, `ATTACH`, etc.).
   * Função SQLite customizada `LIKE` com normalização Unicode NFD sem acento e case-insensitive.
   * Política de leitura baseada em AST (`ReadPolicy` via `sqlglot`) bloqueando incondicionalmente tabelas internas não expostas, colunas sensíveis e `SELECT *`.

---

## 2. Inventário de Tabelas e Relacionamentos

### 2.1 Entidades Principais e Heranças

| Tabela | Superclasse | Descrição e Identificadores |
| :--- | :--- | :--- |
| `organizacao` | — | Superclasse de instituições, campi e órgãos de fomento |
| `instituicao_lattes` | `organizacao` | Subclasse com `sigla` e `pais` |
| `instituicao_parceira_cnpq` | `organizacao` | Subclasse com `sigla` e `uf` |
| `pessoa` | — | Superclasse de indivíduos (`nome`; sem CPF por LGPD) |
| `pessoa_lattes` | `pessoa` | Perfil Lattes (`id_lattes`, `url_lattes`, etc.) |
| `pessoa_src` | `pessoa` | Papel de pessoa do SRC |
| `pesquisador` | `pessoa` | Papel de pesquisador (`id_titulacao`, `id_organizacao`) |
| `estudante` | `pessoa` | Papel de discente (`id_campus`, `id_nivel_treinamento`, `id_curso`) |
| `grupo_pesquisa` | — | Superclasse de grupos de pesquisa |
| `grupo_pesquisa_cnpq` | `grupo_pesquisa` | Grupo DGP CNPq (`situacao_grupo`, `ano_formacao`, datas) |
| `iniciativa` | — | Superclasse de iniciativas institucionais |
| `acao` | `iniciativa` | Ação de extensão/ensino do SRC (`id_origem`, `processo`, etc.) |
| `projeto_pesquisa` | `iniciativa` | Projeto de pesquisa SigPesq (`id_origem`, datas, sigilo, etc.) |
| `projeto_lattes` | `iniciativa` | Projeto declarado no Lattes |
| `producao` | — | Superclasse abstrata de produções |
| `artigo_trabalho_evento` | `producao` | Publicações em periódicos e congressos |
| `livro_capitulo` | `producao` | Livros e capítulos |
| `producao_tecnica_artistica_bibliografica`| `producao` | Softwares sem patente, trabalhos técnicos, etc. |
| `patente_registro` | `producao` | Patentes, marcas e registros (`id_instituicao_depositante NULLABLE`) |
| `membro_grupo` | — | Superclasse de vinculação a grupos |
| `membro_grupo_cnpq` | `membro_grupo` | Participação no grupo DGP (`status_participacao`) |
| `membro_equipe_execucao_src`| `membro_grupo` | Execução em atividades do SRC |

### 2.2 Classes Associativas e Junções N:N

| Tabela | Tipo | Chave Primária | Entidades Relacionadas |
| :--- | :--- | :--- | :--- |
| `parceria_grupo` | Assoc. Class | `id` | `grupo_pesquisa_cnpq` ↔ `instituicao_parceira_cnpq` |
| `membro_projeto` | Assoc. Class | `id` | `pessoa_lattes` ↔ `projeto_lattes` |
| `fomento_projeto` | Assoc. Class | `id` | `organizacao` ↔ `projeto_lattes` |
| `participacao_evento`| Associative | `id` | `pessoa_lattes` ↔ `evento_cientifico` |
| `proficiencia_idioma`| Associative | `id` | `pessoa_lattes` ↔ `idioma` |
| `pessoa_lattes_titulacao` | N:N Pura | Composta | `pessoa_lattes` ↔ `titulacao` |
| `lideranca_grupo_pesquisa` | N:N Pura | Composta | `grupo_pesquisa` ↔ `pesquisador` |
| `grupo_pesquisa_grande_area`| N:N Pura | Composta | `grupo_pesquisa_cnpq` ↔ `grande_area` |
| `cooperacao_grupo_externo_projeto`| N:N Pura| Composta | `grupo_pesquisa_externo` ↔ `projeto_pesquisa` |
| `fomento_acao` | N:N Pura | Composta | `organizacao` ↔ `acao` |
| `acao_campus` | N:N Pura | Composta | `organizacao` ↔ `acao` |
| `parceiro_demandante_projeto`| N:N Pura | Composta | `organizacao` ↔ `projeto_pesquisa` |
| `participacao_estudante_projeto`| N:N Pura | Composta | `estudante` ↔ `projeto_pesquisa` |
| `autoria_producao` | N:N Pura | Composta | `pessoa_lattes` ↔ `producao` |
| `participacao_pesquisador_projeto`| N:N Pura| Composta | `pesquisador` ↔ `projeto_pesquisa` |
| `membro_banca_examinadora` | N:N Pura | Composta | `banca_examinadora` ↔ `pessoa_lattes` |
| `grupo_pesquisa_projeto` | N:N Pura | Composta | `grupo_pesquisa` ↔ `projeto_pesquisa` |
| `grupo_pesquisa_equipamento`| N:N Pura | Composta | `grupo_pesquisa_cnpq` ↔ `equipamento_software` |
| `grupo_pesquisa_linha_pesquisa`| N:N Pura | Composta | `grupo_pesquisa_cnpq` ↔ `linha_pesquisa` |
| `pesquisador_linha_pesquisa`| N:N Pura | Composta | `pessoa_lattes` ↔ `linha_pesquisa` |

---

## 3. As 6 Tabelas Fato Analíticas (Views Dinâmicas v2.0)

As 6 views incorporam as 12 correções de consistência e novos campos da especificação v2.0:

1. **`vfact_extensao_acao_resolved`**:
   - Agrega campi com `GROUP_CONCAT` ordenado sem duplicação (`acao_campus`).
   - Agrega fomento com `GROUP_CONCAT` sem duplicação (`fomento_acao`).
   - Inclui `qtd_atividades_vinculadas` via subselect desacoplado.
   - `ano_cadastro` e `mes_cadastro` calculados via `strftime`.
2. **`vfact_extensao_participacao_resolved`**:
   - Chave composta única por participante e atividade.
   - Inclui `flag_certificado` e `flag_aprovado`.
3. **`vfact_projeto_pesquisa_resolved`**:
   - `origem_registro`: `'CADASTRO_COMPLETO_SIGPESQ'` vs `'INFERIDO_DE_ORIENTACAO'`.
   - `flag_projeto_completo`: `1` para cadastros completos do SigPesq e `0` para inferidos.
   - `duracao_meses_prevista`: calculada via `julianday`.
   - `parceiros_demandantes`: agregados com `GROUP_CONCAT` a partir de `parceiro_demandante_projeto`.
   - `qtd_planos_trabalho`: contagem via subselect.
4. **`vfact_orientacao_bolsa_resolved`**:
   - `duracao_meses_efetiva`: cálculo proporcional resiliente a cancelamentos parciais e totais.
   - `investimento_total_estimado` e `investimento_previsto_original`: cálculo de bolsas financeiras.
   - `titulacao_orientador`, `nivel_treinamento_aluno`, `curso_orientado`.
5. **`vfact_producao_cientifica_resolved`**:
   - `qtd_autorias`: total de coautores vinculados via `autoria_producao`.
   - `flag_obra_unica`: `1 / COUNT(*) OVER (PARTITION BY id_producao)` para evitar contagem inflada de produções com múltiplos autores do IFES.
   - `flag_software_sem_patente`: identificação de softwares registrados sem patente.
   - `instituicao_vinculo`: organização de vínculo do pesquisador.
6. **`vfact_grupo_pesquisa_membro_resolved`**:
   - `flag_ativo`: `1` para membros atuais e `0` para egressos.
   - Linhas e grandes áreas agregadas via subselects.
