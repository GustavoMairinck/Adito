# Requirements — ETL e Banco Analítico DuckDB OLAP do Adito

**Status:** REQUIREMENTS_READY (rev. 1 aprovada em 2026-11-10; rev. 2 aprovada em 2026-11-12; rev. 3 aprovada em 2026-11-13)
**Discovery de origem:** `docs/discovery/adito.md` (rev. 4, rev. 5 e rev. 6, PROBLEM_READY)
**Classificacao de Processo:** NORMAL PROCESS
**Recorte:** o ETL em `etl/` (fases de extração e cruzamento), a exportação JSON de 41 tabelas (`Adito/scripts/exportar_json.py`) e a geração do banco analítico DuckDB OLAP (`Adito/scripts/gerar_duckdb.py` com as 6 tabelas fato materializadas `vfact_*_resolved`) + adaptação do `Adito/app/backend/` para DuckDB e contexto `pesquisa-extensao-ifes`.

## Intent Summary

A equipe de dados roda, na própria máquina, um extrator por fonte que baixa o bruto sem banco nem servidor, depois um script que liga as pessoas entre as quatro bases pelo nome normalizado, popula o banco PostgreSQL `unificado` (`Adito/scripts/popular_banco.py`) e executa `Adito/scripts/exportar_json.py` para tirar uma fotografia consistente (somente leitura) das 41 tabelas necessárias às 6 views analíticas (`vfact_*_resolved`) em arquivos JSON acompanhados de um `manifesto.json` de schema. Em seguida, `Adito/scripts/gerar_duckdb.py` compila essa fotografia no banco colunar embutido `Adito/app/data/dados.duckdb` com as 6 tabelas fato materializadas para alimentar o backend analítico do Adito. Em nenhum arquivo do ETL, da exportação ou do DuckDB aparece dado pessoal além do nome (e endereços profissionais/de grupo autorizados).

## Functional Requirements

### Extração — SRC (primeiro)
- **FR01** — O extrator de ações do SRC lista as ações do campus pela consulta pública, baixa o detalhe de cada ação e os vínculos de ação-mãe → filhas, e grava `etl/brutos/src/acoes/acao_<id>.json` mais `_index.json`, no mesmo formato do SRCEtl.
- **FR02** — O extrator de participações do SRC entra com a credencial da equipe e, para cada processo do `_index.json`, lê as atividades e, de cada atividade, o público-alvo e a equipe de execução, gravando `etl/brutos/src/participacoes/participacoes_<processo>.json`.
- **FR03** — O extrator de participações retoma de onde parou: processos já gravados são pulados, e cada processo é gravado assim que termina.

### Extração — fontes do horizon_etl (depois)
- **FR04** — O extrator do SigPesq baixa os relatórios de grupos, projetos e orientações (pela biblioteca `sigpesq-agent`) e grava cada relatório como JSON em `etl/brutos/sigpesq/<relatorio>/`.
- **FR05** — O extrator do CNPq/DGP lê as URLs de espelho dos grupos no bruto do SigPesq, baixa cada espelho (pela `dgp-cnpq-lib`) e grava `etl/brutos/cnpq/grupo_<id16>.json`. URLs fora do formato do espelho são listadas e puladas.
- **FR06** — O extrator do Lattes lê uma lista de entrada (nome, id Lattes), baixa cada currículo (pelo `scriptLattes`) e grava o bruto em `etl/brutos/lattes/`.

### Comum aos extratores
- **FR07** — Cada extrator é um comando próprio, roda sozinho e mostra o progresso.
- **FR08** — A falha em uma unidade (uma ação, um processo, um grupo, um currículo) não interrompe as demais. No fim, o extrator lista o que falhou.
- **FR09** — Cada extrator grava `etl/brutos/<fonte>/_extracao.json` com data e hora, versão do código, contagens e falhas.

### Cruzamento
- **FR10** — O script de cruzamento lê os brutos das quatro fontes e extrai as pessoas de cada uma (nome, papel e referência ao registro de origem: ação/atividade, grupo, projeto, orientação, currículo).
- **FR11** — O cruzamento liga as pessoas entre as fontes pelo nome normalizado (BR02/BR03) e grava `etl/trabalho/pessoas.json` (um id opaco por pessoa, nome e lista de ocorrências por fonte).
- **FR12** — O cruzamento grava as ligações que não são de pessoa: grupo SigPesq ↔ CNPq pelo id de 16 dígitos do espelho e orientação SigPesq ↔ Lattes por título normalizado + orientador normalizado.
- **FR13** — O cruzamento gera `etl/trabalho/relatorio_cruzamento.md` com: pessoas por fonte, pares ligados por par de fontes, nomes sem par em cada fonte e nomes ambíguos não ligados (com as ocorrências de cada um).

### Exportação JSON de Fatos (`Adito/scripts/exportar_json.py` — rev. 2)
- **FR14** — O script `Adito/scripts/exportar_json.py` fornece interface CLI (`argparse`, `--help` em português) com as opções `--saida <pasta>` (padrão `Adito/etl/saida/json/`), `--modo docker|conexao` (padrão `docker`), `--servico <nome>`, `--banco <nome>` e `--usuario <nome>` (lidos por padrão de `Adito/scripts/docker-compose.yml` e `.env`/`.env.example`), `--tabelas a,b,c` (subconjunto da lista oficial), `--forcar` (sobrescreve pasta com JSONs existentes) e `--so-validar <pasta>` (executa apenas a validação pós-exportação sobre uma pasta existente, sem conectar ao banco).
- **FR15** — Antes de exportar, o script confere que todas as tabelas solicitadas existem no schema `unificado` e que o banco não está vazio; se faltar tabela ou o banco estiver vazio, aborta com mensagem clara sem criar nem popular nada.
- **FR16** — Toda a leitura do banco ocorre em uma única sessão do `psql` dentro de `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;` encerrada com `ROLLBACK;`, garantindo fotografia consistente no mesmo instante e bloqueando qualquer escrita.
- **FR17** — Para cada tabela exportada, o PostgreSQL gera o JSON (`coalesce(json_agg(t ORDER BY <ordem>), '[]'::json)`) sem corrupção por escape de texto, ordenado pela chave primária descoberta no catálogo (`pg_index`) ou por todas as colunas na ordem da tabela quando não houver PK. Cada tabela é gravada em `<saida>/<tabela>.json` (UTF-8, lista de objetos, escrita atômica via arquivo temporário + rename) e validada imediatamente com `json.loads`.
- **FR18** — O script consulta `pg_catalog` (`pg_attribute`, `format_type`, `pg_index`, `pg_constraint`, `pg_enum`) e `SHOW server_version;` e grava `<saida>/manifesto.json` contendo `gerado_em` (ISO 8601 UTC), `commit` atual do git, `proposta` (`arquivo` e `commit`), `postgres` e, por tabela exportada, `linhas`, `colunas` (`nome`, `tipo` exato, `anulavel`, `valores_enum` opcional), `chave_primaria` e `chaves_estrangeiras` (`coluna`, `referencia` e `destino_exportado`).
- **FR19** — Após gravar os arquivos, o script varre todos os JSONs gerados procurando padrões de CPF e e-mail (mesma regra de `popular_banco.py` / `adito_etl.pii`); se encontrar qualquer ocorrência, apaga os arquivos gerados e aborta informando apenas tabela e coluna (nunca o valor encontrado).
- **FR20** — No final da exportação (e quando chamado com `--so-validar <pasta>`), o script executa a validação completa: (a) todo `<tabela>.json` listado no manifesto existe, é JSON válido, é uma lista e tem exatamente `linhas` itens; (b) as chaves de cada objeto batem com os nomes das colunas do manifesto na mesma ordem; (c) integridade referencial para toda FK com `destino_exportado: true` (todo valor não nulo existe na coluna referenciada do arquivo de destino); (d) lista no resumo as FKs com `destino_exportado: false` e imprime resumo por tabela (linhas, colunas, tamanho em bytes e FKs verificadas).

### Banco Analítico DuckDB OLAP e Adaptação do Adito (rev. 3)
- **FR21** — O script `Adito/scripts/gerar_duckdb.py` lê `Adito/etl/saida/json/manifesto.json` e os 41 arquivos `<tabela>.json`, cria o arquivo `Adito/app/data/dados.duckdb` (ou caminho configurado via `--saida` / `ORACULO_DADOS_DB`) de forma idempotente, carrega as 41 tabelas no schema `unificado` com os tipos mapeados do `manifesto.json` e valida a contagem de linhas de cada tabela.
- **FR22** — O `gerar_duckdb.py` executa os 6 SQLs de `Docs/Fatos/PropostaFatos.md` e **materializa as 6 tabelas fato (`CREATE TABLE main.vfact_*_resolved AS SELECT ...`)** em formato colunar no schema `main` do DuckDB (além de views equivalentes em `unificado.vfact_*_resolved`), validando ao final as contagens exatas (`vfact_extensao_acao_resolved=207`, `vfact_extensao_participacao_resolved=6741`, `vfact_projeto_pesquisa_resolved=236`, `vfact_orientacao_bolsa_resolved=1203`, `vfact_producao_cientifica_resolved=1232`, `vfact_grupo_pesquisa_membro_resolved=553`).
- **FR23** — A camada analítica de `Adito/app/backend/` (`core/datastore.py`, `core/contexts.py`, `analytics_index/services.py` e `dashboard/views.py`) conecta ao `dados.duckdb` em modo somente-leitura (`read_only=True`) com defesa em profundidade nativa (`enable_external_access=False` e `lock_configuration=True`), mantendo `app.db` em SQLite para o Django e o checkpointer do LangGraph, e provendo compatibilidade de linhas/dicionários e introspecção de colunas (`view_columns`) no DuckDB.
- **FR24** — O validador de segurança SQL (`agents/bi_agent/sql_security.py`, `agent.py`, `graph.py`, `tool.py`, `nodes/sql_validator.py`) opera no dialeto `duckdb` (`sqlglot`), permitindo apenas consultas `SELECT` sobre as 6 tabelas fato declaradas em `allowed_tables`, bloqueando comandos de escrita/sistema (`COPY`, `ATTACH`, `DETACH`, `INSTALL`, `LOAD`, `PRAGMA`, `SET`, `CALL`, `EXPORT`, `IMPORT`), funções de leitura de arquivos externos (`read_csv*`, `read_parquet*`, `read_json*`, `parquet_scan`, `iceberg_scan`, `delta_scan`) e referências às `sensitive_columns` (`*cpf*`, `*email*`).
- **FR25** — O contexto `Adito/app/contexts/pesquisa-extensao-ifes/` é criado com `views.json` (6 tabelas fato, `sensitive_columns`, `embed_columns`, `local_search_columns`, `llm_row_limit: 50`), `rules.md` (regras de grão N:N, `COUNT(DISTINCT ...)`, orçamento vs. bolsa, códigos `'NI'`) e `examples.json` (exemplos pergunta → SQL DuckDB sem nomes reais de pessoas), enquanto `Adito/app/contexts/exemplo-vendas/views.json` permanece desativado (`"ativo": false`, suportado por `load_context_dir`).

## Business / Domain Rules

- **BR01** — Nenhum arquivo do ETL guarda CPF, e-mail, telefone, fax, celular ou data de nascimento. *(Rev. 2026-11-11, decisão do usuário: além do nome, entra o endereço profissional do Lattes, sem telefone, e o endereço do grupo no CNPq; informações de contato continuam fora.)* Os extratores descartam esses campos na coleta, guardando só as colunas de uma **lista de permitidas** por fonte (nome mais campos não pessoais, como situação, função e carga horária). Coluna nova que não está na lista é descartada e avisada.
- **BR02** — Nome normalizado = sem acento, minúsculo, pontuação vira espaço, espaços únicos. *(Rev. 2026-11-10, a pedido do usuário: mesma inferência do horizon_etl.)* Dois nomes são a mesma pessoa quando coincide (a) a forma normalizada, (b) a forma sem partículas (da, de, di, do, dos, das, du, del, dela, e, y) e com "Jr" = "Junior" ou (c) as mesmas palavras em outra ordem. A ligação é transitiva. Filho/Neto/Sobrinho continuam distintos. Nome com menos de duas palavras fora títulos ("Dr", "Maria") não liga e vai para o relatório.
- **BR03** — Nomes ligados pela BR02 são a mesma pessoa em todas as fontes. A exceção é quando uma fonte com id próprio de pessoa (id Lattes do titular do currículo) tem **dois ids diferentes** no mesmo grupo de nomes: são homônimos, não ligam e vão para o relatório. (O espelho do CNPq não traz id por membro.)
- **BR04** — Ordem de execução: o SigPesq roda antes do CNPq (as URLs de espelho vêm dele). SRC e Lattes não dependem de outra fonte.
- **BR05** — O id opaco de pessoa não carrega CPF, e-mail nem hash deles.
- **BR06** — O código é copiado para `etl/` sem alterar os repositórios SRCEtl e horizon_etl. O README do `etl/` registra o repositório e o commit de origem de cada extrator.
- **BR07** *(rev. 2)* — A lista oficial de tabelas exportáveis é definida como constante no código agrupada pelas 6 views de `Docs/Fatos/PropostaFatos.md` (commit `c91761a`), totalizando **41 tabelas** (40 referenciadas nos blocos `CREATE OR REPLACE VIEW` mais `parceiro_demandante_projeto` listada na seção 3.3.3). Qualquer nome passado em `--tabelas` fora dessa constante é recusado.
- **BR08** *(rev. 2)* — As tabelas são exportadas completas (todas as linhas e colunas, sem filtro); tabela vazia sai como `[]`. A exportação é das tabelas base, nunca das views (que serão recriadas no DuckDB de destino).
- **BR09** *(rev. 2)* — O PostgreSQL é estritamente somente leitura para `exportar_json.py`: é proibido qualquer comando `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY ... FROM` ou `GRANT` no script. O teste das 6 views da proposta é feito exclusivamente em transação avulsa encerrada com `ROLLBACK;`.
- **BR10** *(rev. 2)* — Antes de gravar qualquer arquivo, `exportar_json.py` verifica se a pasta de saída está ignorada pelo git (`git check-ignore -q <saida>/x.json`); se não estiver ignorada, recusa a execução para impedir commit acidental de nomes reais de pessoas (`pessoa.json`, `orientacao.json`). Se a pasta de saída já contiver JSONs e `--forcar` não for informado, o script também recusa sobrescrever.
- **BR11** *(rev. 3)* — As 6 tabelas fato no DuckDB (`vfact_*_resolved`) são materializadas como tabelas físicas colunares (`CREATE TABLE`) no schema `main` para máxima velocidade de leitura OLAP sem `JOIN` em tempo de execução.
- **BR12** *(rev. 3)* — Colunas sensíveis (`sensitive_columns`: CPF e e-mail) permanecem ocultas do DDL enviado à LLM (`describe_views`) e bloqueadas tanto na validação de SQL (`validate_read_only_sql` / `SELECT *` sem projeção segura) quanto na política de conexão (`connect_dados`).
- **BR13** *(rev. 3)* — Nenhum nome real de pessoa da base pode aparecer em código, testes, `examples.json` ou documentação.

## Non-Functional Requirements

- **NFR01** — Sem banco, Prefect, Supabase, `research-domain`/`eo_lib`, Telegram ou LLM em nenhuma fase de extração e cruzamento. *(Rev. 2026-11-11: o Infisical volta como origem das credenciais, ver NFR02; a carga no banco unificado é feita por `Adito/scripts/popular_banco.py`, fora do ETL.)*
- **NFR02** — As credenciais (SRC e SigPesq) vêm do Infisical (`ADITO_CREDENCIAIS=infisical`, mesma identidade de máquina do horizon_etl) ou do `etl/.env` (`ADITO_CREDENCIAIS=env`), escolha explícita; a configuração fica em `etl/.env`, fora do git, e nenhum valor aparece em log nem em arquivo gerado. *(Rev. 2026-11-11, pedido do usuário.)*
- **NFR03** — O `etl/` tem `pyproject.toml` e ambiente Python próprios, separados do sidecar do app. Dependências a aprovar: Playwright, httpx, beautifulsoup4, pydantic, `sigpesq-agent`, `dgp-cnpq-lib`, `scriptLattes` (e o que estas exigirem, como selenium e openpyxl).
- **NFR04** — A coleta autenticada no SRC é sequencial numa única sessão (o SRC aceita uma sessão por usuário). As requisições se identificam por user-agent, e erros de limite (429) esperam antes de tentar de novo.
- **NFR05** — Rodar a mesma extração duas vezes sobre a mesma fonte dá o mesmo bruto, salvo mudança na própria fonte. O cruzamento é determinístico para os mesmos brutos.
- **NFR06** — Há testes automatizados para: a normalização de nomes (BR02); a regra de ambíguos (BR03); e o filtro de dado pessoal (BR01), que falha se aparecer CPF ou e-mail em qualquer arquivo de `etl/brutos/` ou `etl/trabalho/`.
- **NFR07** *(rev. 2)* — `Adito/scripts/exportar_json.py` utiliza **exclusivamente a biblioteca padrão do Python** (Python 3.10+) e o binário `psql` (no container Docker ou local via variáveis da `libpq`), sem adicionar pacotes externos (`psycopg`, `duckdb`, etc.) e sem gravar senhas em código, README ou logs.
- **NFR08** *(rev. 2)* — A exportação JSON é determinística: duas execuções consecutivas sobre o mesmo banco produzem arquivos `<tabela>.json` idênticos byte a byte (variando apenas o campo `gerado_em` no `manifesto.json`).
- **NFR09** *(rev. 2)* — Há testes unitários em `Adito/etl/tests/test_exportar_json.py` (rodando sem depender de Docker, apenas com dados sintéticos como `"Maria Exemplo"`, nunca nomes reais do banco) cobrindo: geração do SQL com ordem por PK e por todas as colunas quando sem PK; recusa de tabela fora da constante de 41 tabelas; ausência de comandos SQL de escrita no código-fonte de `exportar_json.py`; recusa de pasta não ignorada pelo git; detecção de CPF e e-mail nos JSONs gerados; e `--so-validar` (aceita conjunto coerente e rejeita contagem divergente, coluna faltando/fora de ordem e FK quebrada).
- **NFR10** *(rev. 2)* — `Adito/scripts/README.md` inclui a seção `"Exportar JSON para o DuckDB"` documentando propósito, pré-requisitos, modos `docker` e `conexao`, lista das 41 tabelas e como atualizá-la, formato dos arquivos e do `manifesto.json`, tabela de tipos PostgreSQL → JSON, aviso de LGPD e exemplo ilustrativo de leitura no DuckDB com `read_json`.
- **NFR11** *(rev. 3)* — `duckdb>=1.2.0` é adicionado em `Adito/app/backend/requirements.txt`, mantendo o `app.db` em SQLite inalterado.
- **NFR12** *(rev. 3)* — A geração de `dados.duckdb` por `Adito/scripts/gerar_duckdb.py` é determinística e idempotente a partir de `Adito/etl/saida/json/`.
- **NFR13** *(rev. 3)* — Há testes automatizados validando: (a) geração do `.duckdb` e contagens das 6 tabelas fato materializadas; (b) `validate_read_only_sql` no dialeto `duckdb` (bloqueio de escrita, funções `read_*`, tabelas fora da whitelist e `sensitive_columns`); (c) carregamento de contextos (`pesquisa-extensao-ifes` ativo e `exemplo-vendas` desativado) e execução de queries via `connect_dados` / `BIAgent.execute_query`.

## User Scenarios

### Main flow
1. A equipe preenche `etl/.env` com as credenciais e roda o extrator de ações do SRC para o campus Serra.
2. Roda o extrator de participações do SRC sobre o `_index.json` gerado.
3. Roda o extrator do SigPesq, depois o do CNPq e o do Lattes.
4. Roda o cruzamento, lê o relatório e confere os ambíguos e os sem par.
5. *(rev. 2)* Popula o banco PostgreSQL `unificado` com `Adito/scripts/popular_banco.py` e roda `python3 Adito/scripts/exportar_json.py`, gerando em `Adito/etl/saida/json/` os 41 arquivos `<tabela>.json` e o `manifesto.json` já validados quanto a JSON, colunas, contagens, integridade referencial e ausência de CPF/e-mail.
6. *(rev. 3)* Executa `python Adito/scripts/gerar_duckdb.py`, que lê o manifesto e os 41 arquivos JSON e materializa as 6 tabelas fato colunares em `Adito/app/data/dados.duckdb`.

### Alternative / Error / Edge cases
- Credencial errada ou sessão expirada no SRC: o extrator para com mensagem clara, sem gravar arquivo parcial do processo em curso, e a próxima execução retoma.
- Página do SRC mudou e um campo some: o campo fica vazio, e o extrator avisa quantos registros vieram sem ele.
- Grupo do SigPesq sem URL de espelho ou com URL inválida: entra na lista de pulados do CNPq.
- Currículo Lattes que não baixa depois das tentativas: entra na lista de falhas, sem travar a fase.
- Nome escrito diferente em duas fontes (abreviação, nome de casada): fica sem par e aparece no relatório.
- Dois homônimos sem id próprio (por exemplo, dois alunos no SRC): viram uma pessoa só. É um risco aceito (BR03).
- *(rev. 2)* Pasta de saída não ignorada pelo git: `exportar_json.py` recusa iniciar a exportação antes de escrever qualquer arquivo.
- *(rev. 2)* Pasta de saída já contém arquivos `.json` e `--forcar` não foi passado: `exportar_json.py` recusa sobrescrever.
- *(rev. 2)* Tabela da constante ausente no schema `unificado` ou banco vazio: `exportar_json.py` para e avisa, sem criar nem popular nada.
- *(rev. 2)* Detecção de padrão de CPF ou e-mail em qualquer JSON exportado: `exportar_json.py` apaga os arquivos gerados e aborta exibindo apenas tabela e coluna.

## Business / Domain Context

- As quatro fontes não têm id comum. Sem CPF e e-mail, o nome normalizado é a única chave de pessoa entre fontes.
- O SRCEtl já tem a extração do SRC funcionando (194 ações do Serra em `data/serra/`).
- No horizon_etl, a extração está misturada com carga em banco: o CNPq lê as URLs dos grupos do banco, e a lista do Lattes está fixa no código (`flows/lattes/download.py`).
- *(rev. 2)* O schema `unificado` em 3FN no PostgreSQL é a base relacional oficial; as 6 views analíticas desnormalizadas (`vfact_*_resolved` de `Docs/Fatos/PropostaFatos.md`) são exportadas para JSON.
- *(rev. 3)* As 6 tabelas fato são materializadas no arquivo DuckDB (`dados.duckdb`) pelo script `gerar_duckdb.py`, provendo alta performance para consultas OLAP executadas pelo backend do Adito.

## Technical Context & Constraints

- Origem do SRC: `SRCEtl/src/src/src_etl/etl/` (`scraper.py`, `detail.py`, `vinculadas.py`, `gerenciar.py`, `pipeline.py`, `models.py`, `cli.py`, `cli_part.py`).
- Origem do SigPesq: `horizon_etl/src/adapters/sources/sigpesq/` (o download é feito pela `sigpesq-agent` e gera XLSX; a credencial hoje vem do Infisical).
- Origem do CNPq: `horizon_etl/src/adapters/sources/cnpq_crawler.py` (sobre a `dgp-cnpq-lib`) e a validação do espelho em `flows/cnpq/groups.py`.
- Origem do Lattes: `horizon_etl/src/flows/lattes/download.py` e `lattes_parser.py` (sobre o `scriptLattes`).
- *(rev. 2)* Banco PostgreSQL `unificado`: serviço `oraculo-postgres` em `Adito/scripts/docker-compose.yml` (banco `oraculo_db`, usuário `oraculo`, porta `5435`), DDL em `Adito/scripts/sql/01_tipos_e_dominios.sql`, `02_tabelas.sql` e `03_relacionamentos_e_juncoes.sql`, populado por `Adito/scripts/popular_banco.py`.
- Python: o SRCEtl usa 3.14. As bibliotecas do horizon_etl precisam ser conferidas na mesma versão. `exportar_json.py` requer Python 3.10+ (apenas biblioteca padrão).
- A equipe roda o ETL no Linux; Windows não é exigido para o ETL.

## Quality Attributes

- **Segurança/LGPD:** BR01, BR10, BR12, BR13, NFR02, NFR06 e FR19 são o centro; dado pessoal fora do nome é defeito bloqueante, e `Adito/etl/saida/json/` e `dados.duckdb` jamais entram no git.
- **Manutenibilidade:** um módulo por fonte, sem acoplamento entre extratores além do arquivo bruto do SigPesq lido pelo CNPq; `exportar_json.py` isolado em `Adito/scripts/` sem dependências de terceiros; `gerar_duckdb.py` isolado com checagem de tipos.
- **Observabilidade:** `_extracao.json` por fonte, relatório do cruzamento, `manifesto.json` + resumo por tabela na exportação JSON e validação de contagens no DuckDB.

## Assumptions

- **A01** — O bruto do SigPesq é o XLSX **convertido para JSON** na própria extração, já filtrado pela lista de permitidas; o XLSX não é guardado (ele pode trazer CPF e e-mail).
- **A02** — A lista de entrada do Lattes vira um arquivo `etl/entradas/lattes.csv` (nome, id Lattes) mantido pela equipe, começando pela lista hoje fixa no horizon_etl. Id Lattes é público, então o arquivo pode ser versionado.
- **A03** — O SRC extrai só o campus Serra por padrão; outros campi continuam possíveis por parâmetro.
- **A04** — ~~As credenciais do SigPesq passam a vir de `etl/.env`, no lugar do Infisical.~~ Revisto em 2026-11-11: o Infisical é a origem padrão, como no horizon_etl atualizado.
- **A05** — O formato do bruto do Lattes é o que o `scriptLattes` produz, convertido para JSON quando ele não produzir JSON.
- **A06** *(rev. 2)* — Tabelas que têm linhas não usadas pelas views (ex.: `iniciativa` com registros de `projeto_lattes` ou `membro_grupo` com registros do SRC) são exportadas inteiras sem filtro, e tabelas vazias (ex.: `patente_registro`) saem como `[]`.
- **A07** *(rev. 2)* — FKs de tabelas exportadas que apontam para tabelas fora da lista das 41 (ex.: `grupo_pesquisa_cnpq.id_endereco -> endereco.id`, `pesquisador.id_organizacao` quando aplicável, etc.) têm `destino_exportado: false` no `manifesto.json` e são listadas no resumo da validação sem causar falha.

## Out of Scope

- Montagem de dados além das 6 views analíticas do DuckDB.
- Criar, alterar ou apagar tabelas, views ou dados no PostgreSQL (`unificado`).
- Popular ou recriar o banco PostgreSQL dentro de `exportar_json.py` ou `gerar_duckdb.py`.
- Exportar as demais 44 tabelas do `unificado` que não são usadas por `Docs/Fatos/PropostaFatos.md`.
- Similaridade (fuzzy) de nomes: LATER.
- Painéis, relatórios e classificação por LLM do SRCEtl e do horizon_etl.
- Agendamento automático das extrações.

## Open Questions

- [BLOCKING? nao] A lista de colunas permitidas por fonte (BR01) depende das colunas reais de público-alvo, equipe e relatórios do SigPesq; é fechada na story de cada extrator.
- [BLOCKING? nao] O id opaco de pessoa é estável entre execuções (por exemplo, derivado do nome normalizado com chave da equipe) ou novo a cada execução? Pergunta herdada do Discovery.

## Key Decisions Proposed

- A ambiguidade só é detectável onde a fonte tem id próprio de pessoa (Lattes, CNPq). No SRC e no SigPesq, homônimos viram a mesma pessoa (BR03).
- O CNPq depende do bruto do SigPesq (BR04), não de banco.
- O bruto não guarda o arquivo original quando ele pode conter CPF ou e-mail (A01); a regra de colunas permitidas vale para todas as fontes.
- As bibliotecas externas do horizon_etl (`sigpesq-agent`, `dgp-cnpq-lib`, `scriptLattes`) são usadas como dependência, não copiadas.
- *(rev. 2)* O próprio PostgreSQL serializa os tipos para JSON via `json_agg(t ORDER BY <ordem>)` em uma única sessão `REPEATABLE READ READ ONLY` encerrada com `ROLLBACK;`, evitando conversões manuais em Python e garantindo consistência transacional entre as 41 tabelas.
- *(rev. 2)* A chave primária e as chaves estrangeiras não são inferidas pelo nome da coluna: são lidas diretamente de `pg_catalog` (`pg_index` e `pg_constraint`) e registradas em `manifesto.json`.
- *(rev. 3)* DuckDB OLAP armazena as 6 tabelas fato fisicamente (`CREATE TABLE`) com índices colunares nativos, consultadas em modo `read_only=True` via dialeto DuckDB com validação estrita de segurança SQL.

## Rastreabilidade → Stories (backlog aprovado em 2026-11-10; US-ETL-08 proposta na rev. 2; US-ADITO-DUCKDB-01 proposta na rev. 3)

| Story | Requisitos |
|---|---|
| US-ETL-01 | FR01, FR07, FR08, FR09, BR06, NFR03, NFR05 |
| US-ETL-02 | FR02, FR03, BR01, NFR02, NFR04, NFR06 (PII) |
| US-ETL-03 | FR04, BR01, A01, A04 |
| US-ETL-04 | FR05, BR04 |
| US-ETL-05 | FR06, A02, A05 |
| US-ETL-06 | FR10, FR11, FR13, BR02, BR03, BR05, NFR06 (normalização, ambíguos) |
| US-ETL-07 | FR12 |
| US-ETL-08 *(rev. 2)* | FR14, FR15, FR16, FR17, FR18, FR19, FR20, BR07, BR08, BR09, BR10, NFR07, NFR08, NFR09, NFR10, A06, A07 |
| US-ADITO-DUCKDB-01 *(rev. 3)* | FR21, FR22, FR23, FR24, FR25, BR11, BR12, BR13, NFR11, NFR12, NFR13 |

FR07–FR09, BR01, NFR01 e NFR03 valem para todos os extratores (US-ETL-01 a 05).

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

Rev. 2 e Rev. 3:
- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- 2026-11-10 (rev. 1): aprovado sem ajustes.
- 2026-11-12 (rev. 2): adicionados FR14–FR20, BR07–BR10, NFR07–NFR10 e A06–A07 para `Adito/scripts/exportar_json.py`. Aprovado sem ajustes.
- 2026-11-13 (rev. 3): adicionados FR21–FR25, BR11–BR13 e NFR11–NFR13 para o banco analítico DuckDB OLAP com as 6 tabelas fato materializadas e adaptação do `Adito/app` (US-ADITO-DUCKDB-01).

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED (rev. 3)

**Aprovado pelo usuario:** rev. 1 sim (2026-11-10); rev. 2 sim (2026-11-12); rev. 3 sim (2026-11-13)
