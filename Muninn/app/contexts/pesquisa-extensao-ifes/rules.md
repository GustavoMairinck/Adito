# Regras de Negócio e Modelagem Dimensional — Pesquisa, Extensão e Produção Científica (Ifes)

O banco de dados acadêmicos **SQLite 3 (`dados.db`)** expõe exclusivamente **6 views analíticas (`vfact_*_resolved`)**. Nunca faça `JOIN` com tabelas fora dessa lista e nunca utilize prefixo de schema (`unificado.`).

---

## 1. Guia de Roteamento entre as 6 Tabelas Fato

1. **`vfact_extensao_acao_resolved` (Grão: 1 Ação de Extensão por linha — `id_acao`)**
   - Use quando a pergunta tratar de **ações, projetos, programas, cursos ou eventos de extensão** cadastrados no SRC, relatórios finais aprovados (`relatorio_aprovado = 1` ou `flag_relatorio_aprovado = 1`), coordenadores de extensão (`coordenador_nome`) ou órgãos de fomento de extensão (`orgao_fomento`).
   - Para contar ações únicas: `COUNT(DISTINCT id_acao)` ou `SUM(qtd_acoes)`.
   - `campus` e `orgao_fomento` são pré-agregados por `; ` para evitar duplicação de linhas (*anti-fan-out*).

2. **`vfact_extensao_participacao_resolved` (Grão: 1 Participação em Atividade de Extensão por linha — `id_participacao`)**
   - Use quando a pergunta tratar de **público atendido, participantes, inscritos, certificados emitidos (`flag_certificado = 1`), aprovação (`flag_aprovado = 1`) ou carga horária cumprida (`SUM(carga_horaria)`)** em atividades de extensão.
   - **Grão N:N:** para total de participações/inscrições use `SUM(qtd_participacoes)` ou `COUNT(*)`; para pessoas distintas atendidas use `COUNT(DISTINCT nome_participante)`.

3. **`vfact_projeto_pesquisa_resolved` (Grão: 1 Projeto de Pesquisa por linha — `id_projeto`)**
   - Use quando a pergunta tratar de **projetos de pesquisa institucional (SigPesq)**, parecer da diretoria (`parecer_diretoria = 'APROVADO'` ou `flag_aprovado = 1`), natureza da pesquisa (`natureza_projeto`: `'PESQUISA_APLICADA'` vs `'PESQUISA_BASICA'`), parceiros demandantes (`parceiros_demandantes`), origem do registro (`origem_registro`: `'CADASTRO_COMPLETO_SIGPESQ'` vs `'INFERIDO_DE_ORIENTACAO'`), projetos completos (`flag_projeto_completo = 1`), coordenadores de pesquisa (`coordenador_nome`) ou planos de trabalho (`qtd_planos_trabalho`).
   - **Atenção à composição da view (`origem_registro`):** projetos com `origem_registro = 'INFERIDO_DE_ORIENTACAO'` (`flag_projeto_completo = 0`) possuem `coordenador_nome`, `natureza_projeto`, `parecer_diretoria`, `data_inicio`, `data_fim`, `ano_inicio` e `ano_fim` como **`NULL`**.
   - **Regra de contagem geral:** em perguntas sobre o total geral de projetos de pesquisa cadastrados, conte **todos** os registros (`COUNT(DISTINCT id_projeto)`) — **nunca** filtre `natureza_projeto IS NOT NULL` nem `flag_projeto_completo = 1`, salvo quando o usuário pedir explicitamente apenas cadastros completos ou projetos com natureza informada.
   - Diferencie rigorosamente **projeto de pesquisa** (`vfact_projeto_pesquisa_resolved`) de **projeto/ação de extensão** (`vfact_extensao_acao_resolved`).

4. **`vfact_orientacao_bolsa_resolved` (Grão: 1 Concessão de Orientação/Bolsa por linha — `id_orientacao`)**
   - Use quando a pergunta tratar de **bolsas de iniciação científica/tecnológica, orientações, planos de trabalho de alunos, programas de fomento (`programa_fomento`), modalidade (`'BOLSISTA'` vs `'VOLUNTARIO'`), agências financiadoras (`agencia_financiadora`: FAPES, CNPq, Ifes) ou estimativas financeiras de bolsas**.
   - **Valores reais de `programa_fomento`:** os códigos são armazenados em **minúsculas e com underscore**: `'pibic'`, `'pibic_jr'`, `'pibiti'`, `'pivic'`, `'propos'`, `'pibic_af'`, `'piviti'`, `'pibic_em'`, `'jtc'`, `'finep'`, `'picti'` (além de `'Não Especificado'`). Ao filtrar um programa específico, use sempre `LOWER(programa_fomento) = 'pibic_em'` (nunca `'PIBIC-EM'` com hífen).
   - **Métricas financeiras (EXCLUSIVAMENTE ESTIMATIVAS):**
     - `valor_bolsa_mensal`: valor mensal nominal previsto para a cota.
     - `investimento_total_estimado`: **estimativa** calculada por datas considerando cortes de cancelamento (`data_cancelado`).
     - `investimento_previsto_original`: **estimativa** original para o período previsto integral (ou 12 meses quando sem datas).
     - `duracao_meses_efetiva`: duração estimada em meses considerando interrupção por cancelamento.
     - **Restrição financeira obrigatória:** a base **não** possui registros de pagamento efetivamente comprovado, folha de pagamento ou empenho. Sempre nomeie esses valores como **estimados**. Se o usuário exigir explicitamente valor comprovadamente pago e recusar estimativas, informe que a base contém apenas estimativas calculadas e **não** apresente `investimento_total_estimado` como pagamento comprovado.

5. **`vfact_producao_cientifica_resolved` (Grão: 1 Autoria de Produção Científica por linha — `id_producao` + `id_pessoa_lattes`)**
   - Use quando a pergunta tratar de **publicações e produções intelectuais do Lattes**: artigos em periódicos (`flag_artigo_periodico = 1`), trabalhos em eventos/congressos, livros/capítulos (`tipo_macro_producao = 'LIVRO_OU_CAPITULO'`), patentes/softwares registrados (`flag_patente_software = 1`), softwares sem registro de patente (`flag_software_sem_patente = 1`) ou veículos de publicação (`veiculo_publicacao`).
   - **Campus (P1):** `campus` reflete estritamente o Campus do Ifes de lotação do autor (`'Serra'`, `'Vitória'`, etc.) ou `'Externo / Não Vinculado'`; a instituição externa consta em `instituicao_vinculo`.
   - **Grão N:N (Autoria):** para total de **obras/artigos únicos** (geral, por ano ou por campus), use SEMPRE **`COUNT(DISTINCT id_producao)`** ou **`SUM(flag_obra_unica)`**; para produtividade por autor (`GROUP BY nome_autor`), use `SUM(qtd_autorias)` ou `COUNT(*)`.

6. **`vfact_grupo_pesquisa_membro_resolved` (Grão: 1 Vínculo de Membro em Grupo de Pesquisa CNPq por linha — `id_membro_grupo`)**
   - Use quando a pergunta tratar de **Grupos de Pesquisa CNPq (DGP)**, situação (`situacao_grupo = 'CERTIFICADO'`), líderes (`flag_lider = 1`), membros ativos vs egressos (`status_participacao = 'ATIVO'` vs `'EGRESSO'`) ou tempo de atuação (`tempo_participacao_dias`).
   - **Grão:** para contar **grupos distintos**, use SEMPRE **`COUNT(DISTINCT id_grupo_pesquisa)`**; para vínculos de membros, use `SUM(qtd_membros)` ou `COUNT(DISTINCT id_membro_grupo)`.

---

## 2. Valores Ausentes (`NULL` vs. Texto Padronizado) e Filtros Textuais

As 6 views combinam colunas com **texto padronizado** e colunas com **`NULL` real**:
- **Colunas com texto padronizado:** `grande_area` e `area_conhecimento` em Extensão (`'Não Informada'`), `orgao_fomento` (`'Recurso Próprio / Sem Fomento'`), `titulacao_coordenador` e `titulacao_membro` (`'Não Informada'`), `parceiros_demandantes` (`'Sem Parceiro Demandante'`), `programa_fomento` (`'Não Especificado'`), `titulo_edital` (`'Sem Edital Vinculado'`), `agencia_financiadora` (`'Recurso Institucional Ifes'`), `campus` (`'Não Informado'`, `'Campus Não Informado'` ou `'Externo / Não Vinculado'` no Lattes).
- **Colunas com `NULL` real (sem texto padronizado):**
  - Projetos: `coordenador_nome`, `natureza_projeto`, `parecer_diretoria`, `data_inicio`, `data_fim`, `ano_inicio`, `ano_fim`, `duracao_meses_prevista`, `grande_area`, `palavras_chave`.
  - Bolsas: `titulacao_orientador`, `nivel_treinamento_aluno`, `curso_orientado`, `nome_cancelador`, `data_cancelado`.
  - Produções: `ano`, `veiculo_publicacao`, `doi`, `issn_isbn`, `natureza_artigo`.
  - Grupos: `sigla_grupo`, `grande_area`, `data_inicio`, `data_fim`, `tempo_participacao_dias`.
- **Regra obrigatória para "sem X informado":** sempre verifique **`col IS NULL OR TRIM(col) = ''`** combinado com o texto padronizado quando aplicável (ex.: `programa_fomento IS NULL OR TRIM(programa_fomento) = '' OR programa_fomento IN ('Não Especificado', 'Não Informado')`). Nunca assuma que ausências existem apenas como texto.
- **Buscas textuais:** em SQLite 3 no Muninn, `LIKE '%termo%'` é **case-insensitive e acento-insensível**, mas `_` dentro de `LIKE` atua como curinga de 1 caractere; apenas na igualdade (`=` ou `LOWER(...) = '...'`) hífen (`-`) não casa com underscore (`_`).
- Nunca selecione colunas sensíveis de CPF ou e-mail e prefira listar colunas explicitamente em vez de `SELECT *`.

---

## 3. Cruzamento entre as 4 Bases (SRC, SigPesq, Lattes e CNPq DGP)

Quando o usuário pedir panorama ou cruzamento envolvendo **múltiplas bases simultaneamente**, combine as views usando CTEs (`WITH ...`) ou `UNION ALL` pelas dimensões conformadas:
- **Por Pessoa / Pesquisador:** `vfact_extensao_acao_resolved.coordenador_nome` = `vfact_projeto_pesquisa_resolved.coordenador_nome` = `vfact_orientacao_bolsa_resolved.nome_orientador` = `vfact_producao_cientifica_resolved.nome_autor` = `vfact_grupo_pesquisa_membro_resolved.nome_membro`.
- **Por Grande Área:** `grande_area` em Extensão, Projetos, Bolsas e Grupos CNPq (lembre que Extensão usa `'Não Informada'`, enquanto Projetos e Grupos admitem `NULL`).
- **Por Ano:** `ano_cadastro` (SRC Ações), `ano_participacao` (SRC Participações), `ano_inicio` (SigPesq Projetos), `ano` (SigPesq Bolsas e Lattes) e `ano_formacao` (CNPq Grupos).
- **Sempre agregue cada tabela fato na sua própria CTE antes de fazer `JOIN`** para evitar produto cartesiano (*fan-out trap*).

---

## 4. Fidelidade Analítica

- **Critério de desempate (`ORDER BY`):** quando o usuário especificar explicitamente um desempate (ex.: "desempate pelo nome do campus"), coloque exatamente essa coluna como segundo critério no `ORDER BY` (ex.: `ORDER BY total_grupos DESC, campus ASC`).
- **Registros sem ano em Produções:** ao filtrar por faixa de anos em `vfact_producao_cientifica_resolved`, considere que existem produções com `ano IS NULL`; informe se foram excluídas do recorte ou apresente-as separadamente quando solicitado.
- **Fatos vs. hipóteses:** limite-se estritamente ao que os dados permitem afirmar; nunca apresente causas externas não registradas na base como fatos comprovados.
