# Requirements — ETL do Adito (extração e cruzamento)

**Status:** REQUIREMENTS_READY (aprovado em 2026-11-10)
**Discovery de origem:** `docs/discovery/adito.md` (rev. 4, PROBLEM_READY)
**Classificacao de Processo:** NORMAL PROCESS
**Recorte:** só o ETL em `etl/`, fases de extração e cruzamento. A montagem do pacote (Parquet, `abrir.sql`, `manifesto.json`) e as adaptações do app para o DuckDB ficam para outro documento de requisitos.

## Intent Summary

A equipe de dados roda, na própria máquina, um extrator por fonte que baixa o bruto sem banco nem servidor, e depois um script que liga as pessoas entre as quatro bases pelo nome normalizado, com um relatório que mostra o que ligou, o que ficou sem par e o que ficou ambíguo. Em nenhum arquivo do ETL aparece dado pessoal além do nome.

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

## Business / Domain Rules

- **BR01** — Nenhum arquivo do ETL guarda CPF, e-mail, telefone, fax, celular ou data de nascimento. *(Rev. 2026-11-11, decisão do usuário: além do nome, entra o endereço profissional do Lattes, sem telefone, e o endereço do grupo no CNPq; informações de contato continuam fora.)* Os extratores descartam esses campos na coleta, guardando só as colunas de uma **lista de permitidas** por fonte (nome mais campos não pessoais, como situação, função e carga horária). Coluna nova que não está na lista é descartada e avisada.
- **BR02** — Nome normalizado = sem acento, minúsculo, pontuação vira espaço, espaços únicos. *(Rev. 2026-11-10, a pedido do usuário: mesma inferência do horizon_etl.)* Dois nomes são a mesma pessoa quando coincide (a) a forma normalizada, (b) a forma sem partículas (da, de, di, do, dos, das, du, del, dela, e, y) e com "Jr" = "Junior" ou (c) as mesmas palavras em outra ordem. A ligação é transitiva. Filho/Neto/Sobrinho continuam distintos. Nome com menos de duas palavras fora títulos ("Dr", "Maria") não liga e vai para o relatório.
- **BR03** — Nomes ligados pela BR02 são a mesma pessoa em todas as fontes. A exceção é quando uma fonte com id próprio de pessoa (id Lattes do titular do currículo) tem **dois ids diferentes** no mesmo grupo de nomes: são homônimos, não ligam e vão para o relatório. (O espelho do CNPq não traz id por membro.)
- **BR04** — Ordem de execução: o SigPesq roda antes do CNPq (as URLs de espelho vêm dele). SRC e Lattes não dependem de outra fonte.
- **BR05** — O id opaco de pessoa não carrega CPF, e-mail nem hash deles.
- **BR06** — O código é copiado para `etl/` sem alterar os repositórios SRCEtl e horizon_etl. O README do `etl/` registra o repositório e o commit de origem de cada extrator.

## Non-Functional Requirements

- **NFR01** — Sem banco, Prefect, Supabase, `research-domain`/`eo_lib`, Telegram ou LLM em nenhuma fase de extração e cruzamento. *(Rev. 2026-11-11: o Infisical volta como origem das credenciais, ver NFR02; a carga no banco unificado é feita por `Adito/scripts/popular_banco.py`, fora do ETL.)*
- **NFR02** — As credenciais (SRC e SigPesq) vêm do Infisical (`ADITO_CREDENCIAIS=infisical`, mesma identidade de máquina do horizon_etl) ou do `etl/.env` (`ADITO_CREDENCIAIS=env`), escolha explícita; a configuração fica em `etl/.env`, fora do git, e nenhum valor aparece em log nem em arquivo gerado. *(Rev. 2026-11-11, pedido do usuário.)*
- **NFR03** — O `etl/` tem `pyproject.toml` e ambiente Python próprios, separados do sidecar do app. Dependências a aprovar: Playwright, httpx, beautifulsoup4, pydantic, `sigpesq-agent`, `dgp-cnpq-lib`, `scriptLattes` (e o que estas exigirem, como selenium e openpyxl).
- **NFR04** — A coleta autenticada no SRC é sequencial numa única sessão (o SRC aceita uma sessão por usuário). As requisições se identificam por user-agent, e erros de limite (429) esperam antes de tentar de novo.
- **NFR05** — Rodar a mesma extração duas vezes sobre a mesma fonte dá o mesmo bruto, salvo mudança na própria fonte. O cruzamento é determinístico para os mesmos brutos.
- **NFR06** — Há testes automatizados para: a normalização de nomes (BR02); a regra de ambíguos (BR03); e o filtro de dado pessoal (BR01), que falha se aparecer CPF ou e-mail em qualquer arquivo de `etl/brutos/` ou `etl/trabalho/`.

## User Scenarios

### Main flow
1. A equipe preenche `etl/.env` com as credenciais e roda o extrator de ações do SRC para o campus Serra.
2. Roda o extrator de participações do SRC sobre o `_index.json` gerado.
3. Roda o extrator do SigPesq, depois o do CNPq e o do Lattes.
4. Roda o cruzamento, lê o relatório e confere os ambíguos e os sem par.

### Alternative / Error / Edge cases
- Credencial errada ou sessão expirada no SRC: o extrator para com mensagem clara, sem gravar arquivo parcial do processo em curso, e a próxima execução retoma.
- Página do SRC mudou e um campo some: o campo fica vazio, e o extrator avisa quantos registros vieram sem ele.
- Grupo do SigPesq sem URL de espelho ou com URL inválida: entra na lista de pulados do CNPq.
- Currículo Lattes que não baixa depois das tentativas: entra na lista de falhas, sem travar a fase.
- Nome escrito diferente em duas fontes (abreviação, nome de casada): fica sem par e aparece no relatório.
- Dois homônimos sem id próprio (por exemplo, dois alunos no SRC): viram uma pessoa só. É um risco aceito (BR03).

## Business / Domain Context

- As quatro fontes não têm id comum. Sem CPF e e-mail, o nome normalizado é a única chave de pessoa entre fontes.
- O SRCEtl já tem a extração do SRC funcionando (194 ações do Serra em `data/serra/`).
- No horizon_etl, a extração está misturada com carga em banco: o CNPq lê as URLs dos grupos do banco, e a lista do Lattes está fixa no código (`flows/lattes/download.py`).

## Technical Context & Constraints

- Origem do SRC: `SRCEtl/src/src/src_etl/etl/` (`scraper.py`, `detail.py`, `vinculadas.py`, `gerenciar.py`, `pipeline.py`, `models.py`, `cli.py`, `cli_part.py`).
- Origem do SigPesq: `horizon_etl/src/adapters/sources/sigpesq/` (o download é feito pela `sigpesq-agent` e gera XLSX; a credencial hoje vem do Infisical).
- Origem do CNPq: `horizon_etl/src/adapters/sources/cnpq_crawler.py` (sobre a `dgp-cnpq-lib`) e a validação do espelho em `flows/cnpq/groups.py`.
- Origem do Lattes: `horizon_etl/src/flows/lattes/download.py` e `lattes_parser.py` (sobre o `scriptLattes`).
- Python: o SRCEtl usa 3.14. As bibliotecas do horizon_etl precisam ser conferidas na mesma versão.
- A equipe roda o ETL no Linux; Windows não é exigido para o ETL.

## Quality Attributes

- **Segurança/LGPD:** BR01, NFR02 e NFR06 são o centro; dado pessoal fora do nome é defeito bloqueante.
- **Manutenibilidade:** um módulo por fonte, sem acoplamento entre extratores além do arquivo bruto do SigPesq lido pelo CNPq.
- **Observabilidade:** `_extracao.json` por fonte e relatório do cruzamento.

## Assumptions

- **A01** — O bruto do SigPesq é o XLSX **convertido para JSON** na própria extração, já filtrado pela lista de permitidas; o XLSX não é guardado (ele pode trazer CPF e e-mail).
- **A02** — A lista de entrada do Lattes vira um arquivo `etl/entradas/lattes.csv` (nome, id Lattes) mantido pela equipe, começando pela lista hoje fixa no horizon_etl. Id Lattes é público, então o arquivo pode ser versionado.
- **A03** — O SRC extrai só o campus Serra por padrão; outros campi continuam possíveis por parâmetro.
- **A04** — ~~As credenciais do SigPesq passam a vir de `etl/.env`, no lugar do Infisical.~~ Revisto em 2026-11-11: o Infisical é a origem padrão, como no horizon_etl atualizado.
- **A05** — O formato do bruto do Lattes é o que o `scriptLattes` produz, convertido para JSON quando ele não produzir JSON.

## Out of Scope

- Montagem do pacote (Parquet, `abrir.sql`, `manifesto.json`) e o teste de PII do pacote.
- Adaptações do app (DuckDB, validador, prompts, RAG).
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

## Rastreabilidade → Stories (backlog aprovado em 2026-11-10)

| Story | Requisitos |
|---|---|
| US-ETL-01 | FR01, FR07, FR08, FR09, BR06, NFR03, NFR05 |
| US-ETL-02 | FR02, FR03, BR01, NFR02, NFR04, NFR06 (PII) |
| US-ETL-03 | FR04, BR01, A01, A04 |
| US-ETL-04 | FR05, BR04 |
| US-ETL-05 | FR06, A02, A05 |
| US-ETL-06 | FR10, FR11, FR13, BR02, BR03, BR05, NFR06 (normalização, ambíguos) |
| US-ETL-07 | FR12 |

FR07–FR09, BR01, NFR01 e NFR03 valem para todos os extratores (US-ETL-01 a 05).

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- 2026-11-10: aprovado sem ajustes.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim (2026-11-10)
