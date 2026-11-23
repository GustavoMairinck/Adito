# Regras de Negócio e Modelagem Dimensional — Pesquisa, Extensão e Produção Científica (Ifes)

O banco **SQLite 3 (`dados.db`)** expõe exclusivamente **6 views analíticas (`vfact_*_resolved`)**. Nunca faça `JOIN` com tabelas fora dessa lista, nunca use prefixo de schema (`unificado.`), nunca use `SELECT *`, `INTERSECT` ou `EXCEPT`, e nunca selecione CPF ou e-mail.

> **REGRA CRÍTICA — `"projetos"` solto (sem dizer "de pesquisa" nem "de extensão"):**
> Quando a pergunta falar apenas **"projetos"**, **"total de projetos"** ou **"projetos no Ifes"** (sem especificar pesquisa ou extensão), **NUNCA** consulte só `vfact_projeto_pesquisa_resolved`. Retorne **SEMPRE** via `UNION ALL` as duas frentes: **Projetos de Pesquisa** (`vfact_projeto_pesquisa_resolved`) + **Projetos de Extensão** (`vfact_extensao_acao_resolved WHERE tipo_acao LIKE 'Projeto'`). Se a pergunta pedir **quantos projetos uma pessoa específica participou**, em Extensão faça `UNION` entre `vfact_extensao_acao_resolved` (`coordenador_nome`) e `vfact_extensao_participacao_resolved` (`nome_participante`) filtrando `tipo_acao LIKE 'Projeto'` para deduplicar por `id_acao`.

---

## 1. As 6 Views Fato (Grão e Regras de Roteamento)

1. **`vfact_extensao_acao_resolved` (1 Ação de Extensão/SRC por linha — `id_acao`)**
   - **Domínio fechado de Extensão:** `"ação"`, `"ações"`, `"ações de extensão"`, `"cursos/eventos/programas de extensão"` consultam **sempre** esta view.
   - **Contagem padrão:** `COUNT(DISTINCT id_acao)` sem filtrar `natureza` nem `tipo_acao`, salvo quando pedido explicitamente (`'Projeto'`, `'Curso'`, `'Evento'`, `'Programa'`, `'Prestação de Serviço'`).
   - **Relatório aprovado:** `flag_relatorio_aprovado = 1`.
   - **`campus` e `orgao_fomento`:** pré-agregados com `; ` — nesta view use **`LIKE '%Termo%'`** (ex.: `campus LIKE '%Serra%'`, `orgao_fomento LIKE '%FAPES%'`).
   - **Sem valores R$:** Extensão não possui coluna monetária.

2. **`vfact_extensao_participacao_resolved` (1 Participação em Atividade de Extensão por linha — `id_participacao`)**
   - Use para **público atendido, pessoas impactadas, participantes, inscritos, certificados (`flag_certificado = 1`), aprovação (`flag_aprovado = 1`) e carga horária (`carga_horaria`)**.
   - **Grão N:N:** total de participações/inscrições/certificados = `COUNT(*)`; **pessoas distintas** = `COUNT(DISTINCT nome_participante)`.
   - **Limite da base:** registra coordenadores (`vfact_extensao_acao_resolved.coordenador_nome`) e participantes (`nome_participante`), mas **não** possui coluna/tabela de `"equipe de execução"`. Se perguntarem por equipe de execução, informe esse limite.

3. **`vfact_projeto_pesquisa_resolved` (1 Projeto de Pesquisa SigPesq por linha — `id_projeto`)**
   - Use para **projetos de pesquisa institucional**, parecer da diretoria (`flag_aprovado = 1` ou `parecer_diretoria = 'APROVADO'`), natureza (`'PESQUISA_APLICADA'` vs `'PESQUISA_BASICA'`), origem (`origem_registro`: `'CADASTRO_COMPLETO_SIGPESQ'` vs `'INFERIDO_DE_ORIENTACAO'`; `flag_projeto_completo`: `1` vs `0`), parceiros (`parceiros_demandantes`) e coordenadores (`coordenador_nome`).
   - **Projetos de pesquisa vs. projetos no geral:**
     - Se pedir **"projetos de pesquisa"**: conte todos os registros (`COUNT(DISTINCT id_projeto)`) sem filtrar `flag_projeto_completo = 1` nem `natureza_projeto IS NOT NULL` (salvo se pedido explicitamente).
     - Se pedir apenas **"projetos"** ou **"projetos no Ifes"** (sem dizer pesquisa nem extensão): **NUNCA** consulte só esta view — consolide via `UNION ALL` com **Projetos de Extensão** (`vfact_extensao_acao_resolved WHERE tipo_acao LIKE 'Projeto'`).
   - **Registros inferidos (`flag_projeto_completo = 0`):** têm `coordenador_nome`, `natureza_projeto`, `parecer_diretoria`, `data_inicio`, `data_fim`, `ano_inicio` e `ano_fim` como `NULL`.

4. **`vfact_orientacao_bolsa_resolved` (1 Concessão de Orientação/Bolsa por linha — `id_orientacao`)**
   - Use para **bolsas, orientações, planos de trabalho, orientadores (`nome_orientador`), orientandos/alunos (`nome_orientado`), programas (`programa_fomento`), modalidade (`'BOLSISTA'` vs `'VOLUNTARIO'`), agências (`agencia_financiadora`) e estimativas financeiras**.
   - **Não existe coluna de coorientador** nesta view; se perguntarem por coorientadores, informe esse limite.
   - **Valores reais:** `programa_fomento` é minúsculo com underscore (`'pibic'`, `'pibic_jr'`, `'pibiti'`, `'pivic'`, `'pibic_em'`, `'pibic_af'`, `'propos'`, etc.) — filtre com `LOWER(programa_fomento) = 'pibic'` (ou `'pibic_em'`, nunca `'PIBIC-EM'`). `nivel_treinamento_aluno` é maiúsculo com underscore (`'GRADUACAO'`, `'ENSINO_MEDIO_2O_GRAU'`, `'MESTRADO'`, `'ESPECIALIZACAO'`).
   - **Cancelamentos e vigência:**
     - **Pessoas** (*"quantos alunos/bolsistas cancelados"*): `COUNT(DISTINCT nome_orientado)`.
     - **Registros** (*"quantas bolsas/orientações canceladas"*): `COUNT(DISTINCT id_orientacao)`.
     - Canceladas no geral: `flag_cancelado = 1`.
     - Canceladas **antecipadamente / precocemente / antes do fim / antes do prazo**: **sempre** exija `flag_cancelado = 1 AND data_cancelado IS NOT NULL AND data_fim IS NOT NULL AND julianday(data_cancelado) < julianday(data_fim)`.
     - Orientações **vigentes / ativas**: exija **sempre** `flag_cancelado = 0` (e `data_fim >= date('now')` quando o foco for vigência atual).
   - **Financeiro e duração efetiva:** use `SUM(investimento_total_estimado)` (já desconta cancelamentos; `investimento_previsto_original` é o previsto integral; `valor_bolsa_mensal` é a cota mensal) e `AVG(duracao_meses_efetiva)` para duração média efetiva em meses. Trate valores R$ sempre como **estimativa calculada**, pois a base não tem folha de pagamento; só recuse se o usuário explicitamente proibir estimativas.

5. **`vfact_producao_cientifica_resolved` (1 Autoria Lattes por linha — `id_producao` + `id_pessoa_lattes`)**
   - Use para **publicações, artigos (`flag_artigo_periodico = 1`), livros/capítulos (`tipo_macro_producao = 'LIVRO_OU_CAPITULO'`), softwares registrados (`flag_patente_software = 1`), softwares sem patente (`flag_software_sem_patente = 1`) e veículos (`veiculo_publicacao`)**.
   - **Obras únicas vs. Autorias vs. Autores:** **obras únicas** = `COUNT(DISTINCT id_producao)` (nunca `SUM(flag_obra_unica)` com filtro de campus/autor); **autorias** = `COUNT(*)` ou `SUM(qtd_autorias)` (**nunca** `COUNT(DISTINCT nome_autor)`); **autores distintos** = `COUNT(DISTINCT nome_autor)`; **autoria exclusiva / autor único** = obras com apenas 1 autor (`id_producao IN (SELECT id_producao FROM vfact_producao_cientifica_resolved GROUP BY id_producao HAVING COUNT(DISTINCT id_pessoa_lattes) = 1)`).
   - **Produções bibliográficas vs. técnicas:** `"produções bibliográficas"` = `tipo_macro_producao IN ('ARTIGO_OU_EVENTO', 'LIVRO_OU_CAPITULO')` (exclui `'TECNICA_ARTISTICA'`).
   - **Campus:** `'Externo / Não Vinculado'` indica autor sem lotação no Ifes (instituição externa em `instituicao_vinculo`). Para autores do Ifes, filtre `campus NOT LIKE 'Externo%'`.

6. **`vfact_grupo_pesquisa_membro_resolved` (1 Vínculo de Membro em Grupo CNPq por linha — `id_membro_grupo`)**
   - Use para **Grupos de Pesquisa CNPq**, situação (`'CERTIFICADO'`, `'CERTIFICADO_NAO_ATUALIZADO'`, `'EM_PREENCHIMENTO'`, `'EXCLUIDO'`; para grupos certificados use `situacao_grupo LIKE 'CERTIFICADO%'`, que inclui o não atualizado), líderes (`flag_lider = 1`), status (`'ATIVO'` vs `'EGRESSO'`, `flag_ativo = 1`), papel (`'Pesquisador'`, `'Estudante'`, `'Técnico'`, `'Membro'`) e tempo de atuação (`tempo_participacao_dias`).
   - **Grupos distintos:** `COUNT(DISTINCT id_grupo_pesquisa)`.
   - **Pessoas distintas vs. Vínculos (membros):**
     - Para **pessoas/integrantes distintos** (*"quantos pesquisadores / líderes / estudantes / técnicos"*, *"integrantes distintos"*): use **`COUNT(DISTINCT nome_membro)`** (ou `COUNT(DISTINCT CASE WHEN ... THEN nome_membro END)`).
     - Para **vínculos / membros ativos agrupados por papel ou por grupo** (*"quantos membros ativos existem agrupados por papel"*, *"grupos com mais membros ativos"*): use **`COUNT(*)`** (com `WHERE flag_ativo = 1`) ou **`SUM(flag_ativo)`** (podendo incluir `COUNT(DISTINCT nome_membro) AS integrantes_distintos` em paralelo).
   - **Papéis (`"pesquisadores"` = SEMPRE esta view):** filtre sempre com `LIKE` (`papel_membro LIKE 'Pesquisador'`, `papel_membro LIKE 'Estudante'`, `papel_membro LIKE 'Técnico%'`), nunca com `IN` em caixa alta. **Nunca** use `coordenador_nome` de pesquisa ou `nome_orientador` para contar `"pesquisadores"`.

---

## 2. Mapa de Papéis e Política de Generalização

| Termo na pergunta | Regra exata |
|---|---|
| **`projetos`** (sem qualificar) | **Generalizável:** `UNION ALL` entre `vfact_projeto_pesquisa_resolved` (Pesquisa) e `vfact_extensao_acao_resolved WHERE tipo_acao LIKE 'Projeto'` (Extensão). |
| **`ações`** / **`extensão`** | **Domínio fechado:** exclusivo de `vfact_extensao_acao_resolved` / `vfact_extensao_participacao_resolved`. |
| **`extensionistas`** | **Domínio fechado (Extensão):** coordenadores (`vfact_extensao_acao_resolved.coordenador_nome`) + participantes (`vfact_extensao_participacao_resolved.nome_participante`). Use `UNION` para total único e `UNION ALL` para detalhar. |
| **`coordenadores`** | Se qualificado (`"coordenadores de pesquisa"` → **só** `vfact_projeto_pesquisa_resolved.coordenador_nome`; `"coordenadores de extensão"` → **só** `vfact_extensao_acao_resolved.coordenador_nome`). Apenas se **sem qualificar** (`"total de coordenadores"`), consolide ambos via `UNION ALL`. |
| **`pesquisadores`** (sem qualificar) | Papel formal `'Pesquisador'` nos Grupos CNPq (`vfact_grupo_pesquisa_membro_resolved WHERE papel_membro LIKE 'Pesquisador'`). **Nunca** use `coordenador_nome` ou `nome_orientador` sozinho como "pesquisadores". |
| **`autores`** (Lattes) | `vfact_producao_cientifica_resolved.nome_autor`. |
| **`orientadores`** / **`orientandos`** | `vfact_orientacao_bolsa_resolved.nome_orientador` / `nome_orientado`. |
| **`líderes de grupo`** | `vfact_grupo_pesquisa_membro_resolved` com `flag_lider = 1`. |
| **`pesquisadores e coordenadores`** (ou 2 papéis juntos) | **Proibido** gerar 2 colunas paralelas roubando papéis. Use `UNION ALL` rotulado listando cada papel na sua view correta. |
| **`docentes / professores / servidores`** | Não existe cadastro de RH/cargo; informe esse limite e use o papel acadêmico correspondente ao contexto da pergunta. |

---

## 3. Regras Transversais de SQL e Qualidade

- **Filtro de `campus` e `LIKE`:** fora de Extensão, `campus` tem valor único por linha — use **`campus LIKE 'Serra'`** (sem `%`, nunca confunde `'Serra'` com `'Centro-Serrano'`). O `LIKE` do Adito é **case-insensitive e acento-insensível** (mas `_` atua como curinga de 1 caractere; em `=`, hífen `-` não casa com `_`). **Nunca** filtre `campus LIKE 'Ifes'` quando a pergunta disser *"no IFES"* (a base inteira já é do IFES; no Lattes use `campus NOT LIKE 'Externo%'` para excluir vínculos externos).
- **Busca por nome de pessoa:** **nunca** use `=` nem `IN (...)` para nomes próprios; use sempre `LIKE` por partes do nome (ex.: `col LIKE '%João%' AND col LIKE '%Silva%'`). Em pergunta aberta sobre uma pessoa (*"histórico / atuação de [Nome]"*), consolide as 6 views via `UNION ALL` usando a coluna de nome de cada view: `vfact_extensao_acao_resolved.coordenador_nome`, `vfact_extensao_participacao_resolved.nome_participante`, `vfact_projeto_pesquisa_resolved.coordenador_nome`, `vfact_orientacao_bolsa_resolved.nome_orientador` / `nome_orientado`, `vfact_producao_cientifica_resolved.nome_autor` e `vfact_grupo_pesquisa_membro_resolved.nome_membro`.
- **Sinônimos de flags:** *"parecer favorável / aprovado pela diretoria"* → `flag_aprovado = 1`; *"softwares sem patente"* → `flag_software_sem_patente = 1`; *"grupos excluídos"* → `situacao_grupo = 'EXCLUIDO'`.
- **Invariância lexical (`"já"`, tempos verbais):** `"já"`, `"ao todo"` e presente/passado retornam o histórico completo; só filtre ativos (`flag_ativo = 1`, `flag_cancelado = 0`, `situacao_grupo <> 'EXCLUIDO'`) quando pedido explicitamente (*"ativos"*, *"vigentes"*, *"atuais"*).
- **Cruzamentos entre views:** agregue/deduplique cada view em sua própria CTE antes de `INNER JOIN` (evita *fan-out*). Colunas de ano por view: `ano_cadastro` (SRC Ações), `ano_participacao` (SRC Participações), `ano_inicio` (SigPesq Projetos), `ano` (SigPesq Bolsas e Lattes) e `ano_formacao` (CNPq Grupos).
- **Rankings e datas:** exclua `'Sem Parceiro Demandante'` / `'Recurso Próprio / Sem Fomento'` em rankings de parceiros/fomentos; use `ORDER BY metrica DESC, nome ASC` determinístico; use `NULLIF` em divisões; para `"ano passado"`, use `CAST(strftime('%Y','now') AS INTEGER) - 1`.
- **Valores ausentes (`NULL` real vs. texto padronizado):**
  - **Texto padronizado:** `grande_area` e `area_conhecimento` em Extensão (`'Não Informada'`), `orgao_fomento` (`'Recurso Próprio / Sem Fomento'`), `titulacao_coordenador` (Projetos) e `titulacao_membro` (Grupos) (`'Não Informada'`), `parceiros_demandantes` (`'Sem Parceiro Demandante'`), `programa_fomento` (`'Não Especificado'`), `titulo_edital` (`'Sem Edital Vinculado'`), `agencia_financiadora` (`'Recurso Institucional Ifes'`), `campus` (`'Não Informado'`, `'Campus Não Informado'` ou `'Externo / Não Vinculado'` no Lattes).
  - **`NULL` real:** Projetos (`coordenador_nome`, `natureza_projeto`, `parecer_diretoria`, `data_inicio`, `data_fim`, `ano_inicio`, `ano_fim`, `duracao_meses_prevista`, `grande_area`, `palavras_chave`); Bolsas (`titulacao_orientador`, `nivel_treinamento_aluno`, `curso_orientado`, `nome_cancelador`, `data_cancelado`); Produções (`ano`, `veiculo_publicacao`, `doi`, `issn_isbn`, `natureza_artigo`); Grupos (`sigla_grupo`, `grande_area`, `data_inicio`, `data_fim`, `tempo_participacao_dias`).
  - **Regra para "sem X informado":** verifique sempre `col IS NULL OR TRIM(col) = ''` combinado com o texto padronizado quando aplicável.
  - **Transparência sobre `ano IS NULL` em Produções:** ao filtrar ou agrupar por ano em `vfact_producao_cientifica_resolved`, considere que existem registros com `ano IS NULL` — informe se foram excluídos ou apresente-os separadamente (`COALESCE(CAST(ano AS TEXT), 'Sem Ano')`) quando solicitado.
