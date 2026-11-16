# Regras de Negócio e Modelagem Dimensional — Pesquisa, Extensão e Produção Científica (Ifes)

O banco analítico **DuckDB OLAP** expõe exclusivamente **6 tabelas fato desnormalizadas (`vfact_*_resolved`)**. Nunca faça `JOIN` com tabelas fora dessa lista e nunca utilize prefixo de schema (`unificado.`).

---

## 1. Guia de Roteamento entre as 6 Tabelas Fato

1. **`vfact_extensao_acao_resolved` (Grão: 1 Ação de Extensão por linha — `id_acao`)**
   - Use quando a pergunta tratar de **ações, projetos, programas, cursos ou eventos de extensão** cadastrados no SRC, relatórios finais aprovados (`relatorio_aprovado = TRUE` ou `flag_relatorio_aprovado = 1`), coordenadores de extensão (`coordenador_nome`) ou órgãos de fomento de extensão (`orgao_fomento`).
   - Para contar ações únicas: `COUNT(DISTINCT id_acao)` ou `SUM(qtd_acoes)`.

2. **`vfact_extensao_participacao_resolved` (Grão: 1 Participação em Atividade de Extensão por linha — `id_participacao`)**
   - Use quando a pergunta tratar de **público atendido, participantes, inscritos, certificados emitidos (`flag_certificado = 1`) ou carga horária cumprida (`SUM(carga_horaria)`)** em atividades de extensão (minicursos, oficinas, palestras).
   - **Atenção ao grão N:N:** Uma mesma pessoa pode participar de múltiplas atividades. Para total de participações/inscrições use `SUM(qtd_participacoes)` ou `COUNT(*)`; para total de pessoas distintas atendidas use `COUNT(DISTINCT nome_participante)`.

3. **`vfact_projeto_pesquisa_resolved` (Grão: 1 Projeto de Pesquisa por linha — `id_projeto`)**
   - Use quando a pergunta tratar de **projetos de pesquisa institucional (SigPesq)**, parecer da diretoria (`parecer_diretoria = 'APROVADO'` ou `flag_aprovado = 1`), natureza da pesquisa (`natureza_projeto`: `'PESQUISA_APLICADA'` vs `'PESQUISA_BASICA'`), coordenadores de pesquisa (`coordenador_nome`) ou quantidade de planos de trabalho por projeto (`qtd_planos_trabalho`).
   - Diferencie rigorosamente **projeto de pesquisa** (`vfact_projeto_pesquisa_resolved`) de **projeto/ação de extensão** (`vfact_extensao_acao_resolved`).

4. **`vfact_orientacao_bolsa_resolved` (Grão: 1 Concessão de Orientação/Bolsa por linha — `id_orientacao`)**
   - Use quando a pergunta tratar de **bolsas de iniciação científica/tecnológica, orientações, planos de trabalho de alunos, programas de fomento (`programa_fomento`: PIBIC, PIBITI, PIBIC-Jr, etc.), modalidade (`'BOLSISTA'` vs `'VOLUNTARIO'`), agências financiadoras (`agencia_financiadora`: FAPES, CNPq, Ifes) ou valores financeiros de bolsas**.
   - **Métricas financeiras:**
     - `valor_bolsa_mensal`: valor mensal pago ao bolsista.
     - `investimento_total_estimado`: valor total investido na bolsa durante a vigência (`SUM(investimento_total_estimado)`).

5. **`vfact_producao_cientifica_resolved` (Grão: 1 Autoria de Produção Científica por linha — `id_producao` + `id_pessoa_lattes`)**
   - Use quando a pergunta tratar de **publicações e produções intelectuais do Lattes**: artigos em periódicos (`subtipo_producao = 'ARTIGO_PERIODICO'` ou `flag_artigo_periodico = 1`), trabalhos em eventos/congressos, livros/capítulos (`tipo_macro_producao = 'LIVRO_OU_CAPITULO'`), patentes/softwares (`flag_patente_software = 1`) ou veículos de publicação (`veiculo_publicacao`).
   - **Atenção ao grão N:N (Autoria):** Uma publicação com $N$ coautores do Ifes aparece em $N$ linhas (uma para cada `nome_autor`).
     - Quando a pergunta pedir **quantas obras/artigos/produções foram publicados no geral, por ano ou por campus**, use SEMPRE **`COUNT(DISTINCT id_producao)`** para não duplicar obras em coautoria.
     - Quando a pergunta pedir **produções por autor/pesquisador específico** (`GROUP BY nome_autor`), pode usar `COUNT(DISTINCT id_producao)` ou `SUM(qtd_producoes)`.

6. **`vfact_grupo_pesquisa_membro_resolved` (Grão: 1 Vínculo de Membro em Grupo de Pesquisa CNPq por linha — `id_membro_grupo`)**
   - Use quando a pergunta tratar de **Grupos de Pesquisa certificados no CNPq (DGP)**, situação do grupo (`situacao_grupo = 'CERTIFICADO'`), líderes de grupo (`flag_lider = 1`), membros ativos vs egressos (`status_participacao = 'ATIVO'` vs `'EGRESSO'`) ou distribuição de pesquisadores e estudantes em grupos.
   - **Atenção ao grão:** Cada linha é um membro em um grupo. Para contar **quantos grupos de pesquisa distintos** existem, use SEMPRE **`COUNT(DISTINCT id_grupo_pesquisa)`** (ou `COUNT(DISTINCT nome_grupo)`). Para contar vínculos de membros, use `SUM(qtd_membros)` ou `COUNT(DISTINCT nome_membro)`.

---

## 2. Tratamento de Valores Não Informados e Filtros Textuais

- Valores ausentes nas dimensões aparecem padronizados como `'Não Informado'`, `'Não Especificado'`, `'Não Informada'`, `'Campus Não Vinculado'` ou `'NI'`. Em rankings analíticos (ex.: top áreas, top agências, top cursos), filtre valores nulos ou não informados quando apropriado.
- No dialeto **DuckDB**, prefira `ILIKE '%termo%'` para buscas textuais case-insensitive (ex.: `campus ILIKE '%Serra%'`).
- Nunca selecione colunas sensíveis de CPF ou e-mail e prefira listar explicitamente as colunas no `SELECT` em vez de `SELECT *`.

---

## 3. Cruzamento entre as 4 Bases (SRC, SigPesq, Lattes e CNPq DGP)

Quando o usuário pedir um panorama ou cruzamento envolvendo **as 4 bases simultaneamente**, combine as 6 tabelas fato usando CTEs (`WITH ...`) ou `UNION ALL` pelas dimensões conformadas:
- **Por Pessoa / Pesquisador**: `vfact_extensao_acao_resolved.coordenador_nome` (SRC) = `vfact_projeto_pesquisa_resolved.coordenador_nome` (SigPesq Projetos) = `vfact_orientacao_bolsa_resolved.nome_orientador` (SigPesq Bolsas) = `vfact_producao_cientifica_resolved.nome_autor` (Lattes) = `vfact_grupo_pesquisa_membro_resolved.nome_membro` (CNPq DGP).
- **Por Grande Área do Conhecimento**: coluna `grande_area` presente em `vfact_extensao_acao_resolved`, `vfact_projeto_pesquisa_resolved`, `vfact_orientacao_bolsa_resolved` e `vfact_grupo_pesquisa_membro_resolved`.
- **Por Ano**: `ano_cadastro` (SRC Ações), `ano_participacao` (SRC Participações), `ano_inicio` (SigPesq Projetos), `ano` (SigPesq Bolsas e Lattes Produções) e `ano_formacao` (CNPq Grupos).
- **Sempre agregue cada tabela fato na sua própria CTE antes de fazer `JOIN`** entre CTEs para evitar produto cartesiano (*fan-out trap*).
