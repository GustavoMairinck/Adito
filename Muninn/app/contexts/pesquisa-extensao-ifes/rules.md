# Regras de Negócio e Modelagem Dimensional — Pesquisa, Extensão e Produção Científica (Ifes)

O banco de dados acadêmicos **SQLite 3 (`dados.db`)** expõe exclusivamente **6 views analíticas dinâmicas (`vfact_*_resolved`)**, operando em modo 100% OLTP sobre 42 tabelas base relacionais em 3FN. Nunca faça `JOIN` com tabelas fora dessa lista e nunca utilize prefixo de schema (`unificado.`).

---

## 1. Guia de Roteamento entre as 6 Tabelas Fato

1. **`vfact_extensao_acao_resolved` (Grão: 1 Ação de Extensão por linha — `id_acao`)**
   - Use quando a pergunta tratar de **ações, projetos, programas, cursos ou eventos de extensão** cadastrados no SRC, relatórios finais aprovados (`relatorio_aprovado = 1` ou `flag_relatorio_aprovado = 1`), coordenadores de extensão (`coordenador_nome`) ou órgãos de fomento de extensão (`orgao_fomento`).
   - Para contar ações únicas: `COUNT(DISTINCT id_acao)` ou `SUM(qtd_acoes)`.
   - `campus` e `orgao_fomento` são pré-agregados por `; ` para garantir que não haja duplicação de linhas (*anti-fan-out*).

2. **`vfact_extensao_participacao_resolved` (Grão: 1 Participação em Atividade de Extensão por linha — `id_participacao`)**
   - Use quando a pergunta tratar de **público atendido, participantes, inscritos, certificados emitidos (`flag_certificado = 1`), aprovação (`flag_aprovado = 1`) ou carga horária cumprida (`SUM(carga_horaria)`)** em atividades de extensão (minicursos, oficinas, palestras).
   - **Atenção ao grão N:N:** Uma mesma pessoa pode participar de múltiplas atividades. Para total de participações/inscrições use `SUM(qtd_participacoes)` ou `COUNT(*)`; para total de pessoas distintas atendidas use `COUNT(DISTINCT nome_participante)`.

3. **`vfact_projeto_pesquisa_resolved` (Grão: 1 Projeto de Pesquisa por linha — `id_projeto`)**
   - Use quando a pergunta tratar de **projetos de pesquisa institucional (SigPesq)**, parecer da diretoria (`parecer_diretoria = 'APROVADO'` ou `flag_aprovado = 1`), natureza da pesquisa (`natureza_projeto`: `'PESQUISA_APLICADA'` vs `'PESQUISA_BASICA'`), parceiros demandantes (`parceiros_demandantes`), origem do registro (`origem_registro`: `'CADASTRO_COMPLETO_SIGPESQ'` vs `'INFERIDO_DE_ORIENTACAO'`), projetos completos (`flag_projeto_completo = 1`), coordenadores de pesquisa (`coordenador_nome`) ou quantidade de planos de trabalho por projeto (`qtd_planos_trabalho`).
   - `duracao_meses_prevista`: duração calculada entre `data_inicio` e `data_fim`.
   - Diferencie rigorosamente **projeto de pesquisa** (`vfact_projeto_pesquisa_resolved`) de **projeto/ação de extensão** (`vfact_extensao_acao_resolved`).

4. **`vfact_orientacao_bolsa_resolved` (Grão: 1 Concessão de Orientação/Bolsa por linha — `id_orientacao`)**
   - Use quando a pergunta tratar de **bolsas de iniciação científica/tecnológica, orientações, planos de trabalho de alunos, programas de fomento (`programa_fomento` — armazenado em minúsculas: `'pibic'`, `'pibiti'`, `'pivic'`, `'pibic_jr'`, `'pibic_em'`, `'pibic_af'`, `'piviti'`, `'propos'`, `'finep'`, `'jtc'`, `'picti'`; use `LOWER(programa_fomento) = 'pibic'` ao filtrar), modalidade (`'BOLSISTA'` vs `'VOLUNTARIO'`), agências financiadoras (`agencia_financiadora`: FAPES, CNPq, Ifes) ou valores financeiros de bolsas**.
   - **Métricas financeiras:**
     - `valor_bolsa_mensal`: valor mensal nominal pago ao bolsista.
     - `investimento_total_estimado`: valor total efetivamente investido na bolsa considerando cortes de cancelamento (`SUM(investimento_total_estimado)`).
     - `investimento_previsto_original`: valor total previsto caso a bolsa tivesse durado os 12 meses integrais.
     - `duracao_meses_efetiva`: duração real calculada em meses considerando interrupção precoce por cancelamento.

5. **`vfact_producao_cientifica_resolved` (Grão: 1 Autoria de Produção Científica por linha — `id_producao` + `id_pessoa_lattes`)**
   - Use quando a pergunta tratar de **publicações e produções intelectuais do Lattes**: artigos em periódicos (`flag_artigo_periodico = 1`), trabalhos em eventos/congressos, livros/capítulos (`tipo_macro_producao = 'LIVRO_OU_CAPITULO'`), patentes/softwares registrados (`flag_patente_software = 1`), softwares sem patente (`flag_software_sem_patente = 1`) ou veículos de publicação (`veiculo_publicacao`).
   - **Atenção à regra de Campus (P1):** A coluna `campus` reflete estritamente o Campus do Ifes de lotação do autor (ex.: `'Serra'`, `'Vitória'`). Se o vínculo for externo, constará `'Externo / Não Vinculado'`. A instituição externa de lotação é informada na coluna `instituicao_vinculo` (ex.: `'Universidade Federal do Espírito Santo'`).
   - **Atenção ao grão N:N (Autoria):** Uma publicação com $N$ coautores do Ifes aparece em $N$ linhas (uma para cada `nome_autor`).
     - Para total de **obras/artigos/produções únicos publicados no geral, por ano ou por campus**, use SEMPRE **`COUNT(DISTINCT id_producao)`** ou **`SUM(flag_obra_unica)`**.
     - Para produtividade por autor/pesquisador específico (`GROUP BY nome_autor`), use `SUM(qtd_autorias)` ou `COUNT(*)`.

6. **`vfact_grupo_pesquisa_membro_resolved` (Grão: 1 Vínculo de Membro em Grupo de Pesquisa CNPq por linha — `id_membro_grupo`)**
   - Use quando a pergunta tratar de **Grupos de Pesquisa certificados no CNPq (DGP)**, situação do grupo (`situacao_grupo = 'CERTIFICADO'`), líderes reais de grupo (`flag_lider = 1`), membros ativos vs egressos (`status_participacao = 'ATIVO'` vs `'EGRESSO'`) ou tempo de atuação em dias (`tempo_participacao_dias`).
   - **Atenção ao grão:** Cada linha é um membro em um grupo. Para contar **quantos grupos de pesquisa distintos** existem, use SEMPRE **`COUNT(DISTINCT id_grupo_pesquisa)`** (ou `COUNT(DISTINCT nome_grupo)`). Para contar vínculos de membros, use `SUM(qtd_membros)` ou `COUNT(DISTINCT nome_membro)`.

---

## 2. Tratamento de Valores Não Informados e Filtros Textuais

- Valores ausentes nas dimensões aparecem padronizados como `'Não Informado'`, `'Não Especificado'`, `'Não Informada'`, `'Externo / Não Vinculado'`, `'Campus Não Informado'` ou `'Sem Edital Vinculado'`.
- No dialeto **SQLite 3**, utilize `LIKE '%termo%'` para buscas textuais. O motor do Muninn provê busca customizada que é **case-insensitive e acento-insensível** (por exemplo, `campus LIKE '%Vitoria%'` e `campus LIKE '%Vitória%'` encontram os mesmos registros).
- Nunca selecione colunas sensíveis de CPF ou e-mail e prefira listar explicitamente as colunas no `SELECT` em vez de `SELECT *`.

---

## 3. Cruzamento entre as 4 Bases (SRC, SigPesq, Lattes e CNPq DGP)

Quando o usuário pedir um panorama ou cruzamento envolvendo **as 4 bases simultaneamente**, combine as 6 tabelas fato usando CTEs (`WITH ...`) ou `UNION ALL` pelas dimensões conformadas:
- **Por Pessoa / Pesquisador**: `vfact_extensao_acao_resolved.coordenador_nome` (SRC) = `vfact_projeto_pesquisa_resolved.coordenador_nome` (SigPesq Projetos) = `vfact_orientacao_bolsa_resolved.nome_orientador` (SigPesq Bolsas) = `vfact_producao_cientifica_resolved.nome_autor` (Lattes) = `vfact_grupo_pesquisa_membro_resolved.nome_membro` (CNPq DGP).
- **Por Grande Área do Conhecimento**: coluna `grande_area` presente em `vfact_extensao_acao_resolved`, `vfact_projeto_pesquisa_resolved`, `vfact_orientacao_bolsa_resolved` e `vfact_grupo_pesquisa_membro_resolved`.
- **Por Ano**: `ano_cadastro` (SRC Ações), `ano_participacao` (SRC Participações), `ano_inicio` (SigPesq Projetos), `ano` (SigPesq Bolsas e Lattes Produções) e `ano_formacao` (CNPq Grupos).
- **Sempre agregue cada tabela fato na sua própria CTE antes de fazer `JOIN`** entre CTEs para evitar produto cartesiano (*fan-out trap*).
