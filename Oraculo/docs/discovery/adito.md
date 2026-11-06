# Discovery — Adito (painel do Campus Serra com oráculo local)

**Status:** PROBLEM_READY
**Classificacao de Processo:** HEAVY PROCESS
**Origem:** hibrido (usuario + codigo + `Oraculo/docs/PORTE_DESKTOP_DECISOES.md`)
**Data:** 2026-11-06 (rev. 3: ids opacos, nomes fora da Mistral, base no repositório do Adito)
**Repositório:** Adito, sobre o porte desktop em `Oraculo/app` (entrou no `development` pelo PR #33)

> "Adito" (do grego *ádyton*, o recinto interno onde o oráculo falava) é o produto desktop derivado do Oráculo-ESX. A versão web continua em `leds-agentes-Oraculo-ESX-main` e não muda.

## Intent

Dar ao Campus Serra um painel generalista de documentos e informações de pesquisa, consultado em linguagem natural por um oráculo que roda na máquina do usuário. O usuário recebe da equipe um pacote de dados pronto (Parquet + `abrir.sql` + `manifesto.json`) e consulta sem rodar ETL, sem instalar banco e sem depender de servidor.

## Problem

- As informações de pesquisa do campus estão espalhadas em quatro fontes (SigPesq, Lattes, CNPq/DGP e SRC) sem identificador em comum; cruzá-las exige trabalho manual.
- O Oráculo-ESX existe como sistema web com servidores (Postgres, Redis, MCP) e preso a uma demo de vendas; não serve para entregar a poucos usuários do campus.
- Os dados envolvem pessoas (estudantes e servidores), então o pacote precisa sair da equipe só com o mínimo de dado pessoal (LGPD).

## Users / Stakeholders relevantes

- **Usuários do campus (poucos):** só consultam; recebem o pacote pronto.
- **Equipe de dados:** guarda os brutos em JSON, monta os Parquet, calcula as ligações entre fontes, gera e entrega o pacote.
- **Donos das fontes:** SigPesq, Lattes, CNPq (DGP) e SRC; o SRC exige credencial para gerar os hashes.
- **Responsável LGPD do campus:** aceita (por ora) nomes em claro no pacote; CPF e e-mail não saem da equipe.
- **Mistral:** recebe pergunta, descrição das views e amostras limitadas; termos de retenção não verificados.

## Current Situation

- O porte desktop em `Oraculo/app` já tem: casca Tauri compilando no Linux, backend Django como sidecar, `app.db` SQLite, checkpointer LangGraph em SQLite (Redis já removido), sem login, chave da Mistral no cofre do SO, modelo `Contexto` com `views.json`, validador com lista de views, histórico só com SQL.
- O dado consultado hoje é um `dados.db` **SQLite** aberto só para leitura com `set_authorizer`; a demo de vendas está em `Oraculo/app/contexts/exemplo-vendas/`. Os arquivos citados no escopo (`exemples.json` e `schema-ddl.sql`, em `Oraculo/app/mudanças/mudanca/`) são da demo de vendas.
- Os modelos Astah de SigPesq, Lattes, CNPq (DGP) e SRC, mais o unificado, estão em `Docs/ModelosClasses/`.
- Teste do usuário: abrir o pacote e criar as views no DuckDB levou cerca de 25 ms.

## Desired Outcome

O usuário abre o Adito no Windows ou no Linux, aponta o pacote recebido e pergunta, por exemplo, "quais orientações do grupo X têm currículo Lattes com o mesmo título". O oráculo responde com SQL DuckDB sobre as views do pacote, sem servidor, e o mesmo pacote dá a mesma resposta nos dois sistemas.

## Success Criteria

- O usuário recebe o pacote e o oráculo responde sem rodar o ETL e sem instalar banco ou servidor.
- O mesmo pacote dá as mesmas respostas em Windows e em Linux.
- Um teste na montagem bloqueia o pacote se aparecer qualquer dado pessoal além do nome, inclusive hash de CPF ou de e-mail (o pacote só leva ids opacos).
- Nenhum nome de pessoa é enviado à Mistral pelo app ou pela montagem (embeddings, prévias de resultado, histórico); só o que o usuário digitar na pergunta.
- O SQL do oráculo não consegue gravar: conexão só leitura, só SELECT e só nas views da lista.
- Todos os pares do `exemples.json` e o SQL do painel rodam no DuckDB sem erro.
- Abrir o pacote e criar as views leva menos de 1 segundo (no teste levou cerca de 25 ms).

## Scope

### IN
- Projeto: painel generalista de documentos e informações do Campus Serra, consultado por um oráculo local (o Oráculo-ESX adaptado).
- Fontes: SigPesq, Lattes, CNPq (DGP) e SRC, tendo os modelos Astah de cada uma como referência.
- Dados brutos: as 4 fontes guardadas em JSON pela equipe.
- Parquet por fonte: os tipos de cada campo vêm do modelo da fonte, e as listas ficam como lista de verdade, não como texto.
- Ligações entre fontes calculadas uma vez, na montagem, e entregues em Parquet:
  - grupo SigPesq ↔ CNPq pelo número do espelho;
  - estudante SigPesq ↔ SRC pelo hash do CPF;
  - servidor pelo hash do e-mail;
  - orientação SigPesq ↔ Lattes pelo título + orientador.
  - *(rev. 3)* As ligações chegam ao pacote por **ids opacos**; os hashes de CPF e e-mail são usados só na montagem e ficam com a equipe.
- DuckDB como banco do oráculo: aberto em memória, só leitura, com as views criadas pelo `abrir.sql` sobre os Parquet.
- Pacote de dados pronto entregue ao usuário: Parquet, `abrir.sql` e `manifesto.json`. O usuário não roda o ETL, e cada pacote novo substitui o anterior inteiro.
- LGPD: nome em claro; CPF e e-mail só como hash, para ligar as fontes; nenhum outro dado pessoal no pacote. *(rev. 3: os hashes não vão no pacote; ele leva ids opacos.)*
- Busca de nomes sem acento, sem depender de extensão baixada da internet. *(rev. 3: é o único jeito de resolver nomes de pessoas; eles não são embedados.)*
- *(rev. 3)* Nomes de pessoas não vão para a Mistral: ficam fora dos embeddings e das linhas de resultado copiadas para o prompt; aparecem só na tela.
- Adaptações do Oráculo para o DuckDB:
  - conexão do BI Agent no DuckDB;
  - `sql_security.py` aceitando a lista de views e só SELECT;
  - prompts dizendo que o dialeto é DuckDB;
  - pares do `exemples.json` e SQL do `dashboard/views.py` revisados (`to_char` vira `strftime`, `unaccent` vira `strip_accents`);
  - `schema-ddl.sql` reescrito como descrição das views para o RAG;
  - ~~embeddings dos nomes calculados na montagem e entregues no pacote;~~ *(rev. 3: removido; nomes de pessoas não são embedados)*
  - bootstrap trocado pela abertura do pacote;
  - dados fictícios removidos.
- Oráculo sem servidores obrigatórios: Redis vira cache em memória e Langfuse fica opcional.
- Funcionar em Windows e Linux.

### OUT
- Horizon: `horizon_etl`, `horizon.db` (SQLite) e os painéis do Horizon e do SRC
- Outras bases: Egressos, Editais e Diretoria
- PostgreSQL, MongoDB e qualquer servidor de banco
- Usuário rodar o ETL
- Usuário editar ou acrescentar dados
- Histórico de cargas e consultas a versões antigas
- Dados brutos no pacote do usuário

### LATER
- Busca textual com a extensão `fts` do DuckDB, empacotada junto com o oráculo
- Busca por sentido em textos longos, como resumos e descrições (LanceDB)
- Consultas de relacionamento em SQL, como "quem orientou quem" (DuckPGQ)
- Camada em estrela (fatos e dimensões) por cima do núcleo, se a equipe decidir

## Constraints / Feasibility

- Só 4 fontes: SigPesq, Lattes, CNPq (DGP) e SRC.
- Formatos: JSON (bruto, só com a equipe), Parquet (pacote) e DuckDB (consulta).
- Versão do DuckDB fixa (2.0.x) para todos, porque os arquivos e as extensões dependem da versão. (Não conferido aqui: o `duckdb` não está instalado neste ambiente.)
- As fontes não têm id em comum. As ligações dependem de nome, título e hash de CPF ou e-mail, e os hashes do SRC dependem de credencial no SRC.
- O oráculo lê os dados só por views, e o validador confere o nome da view.

## Assumptions

- Poucos usuários, e a equipe gera e entrega o pacote.
- Os usuários só consultam os dados.
- Só a versão mais recente dos dados importa.
- Por enquanto, entregar nomes em claro é aceitável para quem recebe.
- O volume é pequeno (dezenas de milhares de linhas), então desempenho não decide nada.
- [ASSUMPTION — agente] Como a base é o porte em `Oraculo/app` (confirmado na rev. 3), continuam valendo as decisões do porte que o escopo não cita: casca Tauri, sem login, chave da Mistral do usuário no cofre do SO, `app.db` SQLite para Django/conversas/dashboards, histórico só com SQL, modelo `Contexto`.
- [ASSUMPTION — agente] O `manifesto.json` marca quais colunas são nomes de pessoas, para o app tirá-las do que vai ao LLM.
- [ASSUMPTION — agente] "Redis vira cache em memória" vale para cache de consultas; o estado das conversas continua no checkpointer SQLite que já existe (em memória ele se perderia ao fechar o app).
- [ASSUMPTION — agente] O `manifesto.json` faz o papel do `views.json` atual (lista de views expostas, descrições, versão do pacote, modelo de embedding).

## Decisões anteriores que este escopo muda

| Antes (`Oraculo/docs/PORTE_DESKTOP_DECISOES.md`) | Agora |
|---|---|
| App agnóstico de dados; nada ligado a SigPesq | Produto do Campus Serra com 4 fontes fixas |
| `dados.db` SQLite copiado pela API de backup, protegido por `set_authorizer` | Pacote Parquet + `abrir.sql`, DuckDB em memória; o DuckDB não tem `set_authorizer`, a defesa fica no validador e na configuração da conexão |
| Colunas sensíveis declaradas por contexto (`sensitive_columns`) | O pacote já sai só com nome + hashes; o teste da montagem garante |
| Nomes de pessoas não são embedados (busca local com FTS5) | Mantido (rev. 3): nomes não são embedados; busca local sem acento (`strip_accents`), FTS do DuckDB fica para depois |
| Índices (RAG, valores) gerados no app com a chave do usuário | Embeddings de valores não pessoais vêm prontos no pacote (a confirmar) |
| Prévia de linhas de resultado vai ao LLM (até 20 linhas) | Continua, mas sem as colunas de nome de pessoa |

## Risks

- **Hash de CPF é reversível** (cerca de 1 bilhão de CPFs possíveis). Mitigado na rev. 3: os hashes ficam só com a equipe e o pacote leva ids opacos. Continua valendo proteger os JSON brutos e os hashes no ambiente da equipe.
- **Ids opacos que mudam a cada montagem** quebram SQL salvo (widgets, histórico) que cite um id literal. O app já mostra "os dados mudaram, refaça a pergunta"; ids estáveis entre montagens evitam isso.
- **Nomes ainda podem chegar à Mistral** pelo que o usuário digitar na pergunta (inevitável, já previsto no aviso de primeiro uso) e por colunas de nome que o SQL gerado selecionar; o app precisa tirá-las da prévia enviada ao LLM e do texto guardado no histórico que volta ao prompt.
- **DuckDB em memória não é "só leitura" por si.** Sem configuração, o SQL gerado poderia criar tabelas, gravar arquivos (`COPY ... TO`), ler arquivos fora do pacote (`read_csv`), anexar bancos ou instalar extensões. Além do validador, a conexão precisa, depois de rodar o `abrir.sql`, limitar o acesso a arquivos à pasta do pacote, desligar instalação/carga automática de extensões e travar a configuração. Os nomes exatos das opções precisam ser conferidos na versão fixada.
- **Modelo de embedding** dos valores não pessoais: se mudar, os vetores do pacote deixam de bater com os da pergunta; o `manifesto.json` precisa registrar o modelo.
- **Qualidade das ligações.** Título + orientador e nomes têm acentos, abreviações, erros de digitação e homônimos. Sem relatório de taxa de ligação por montagem, erros passam despercebidos e viram respostas erradas.
- **Listas no Parquet.** SQL com listas (`unnest`, `list_contains`) é mais propenso a erro do LLM; os exemplos do RAG precisam cobrir esses casos.
- **Versão fixa do DuckDB** precisa ser a mesma no sidecar empacotado (Windows e Linux) e na montagem.
- **Credencial do SRC** para gerar hashes é um ponto único de dependência da equipe.
- Riscos do porte que continuam: empacotar o sidecar Python, SmartScreen no Windows sem assinatura, Secret Service ausente em algumas distros, build do Windows ainda não feito.

## Open Questions

- ~~[BLOCKING] Hashes no pacote?~~ Respondido (rev. 3): ids opacos; hashes ficam com a equipe.
- ~~[BLOCKING] Nomes para a Mistral?~~ Respondido (rev. 3): não vão.
- ~~[BLOCKING] Onde o trabalho acontece?~~ Respondido (rev. 3): no repositório do Adito, sobre `Oraculo/app`.
- [BLOCKING? nao] Os ids opacos são estáveis entre montagens (por exemplo HMAC com chave da equipe) ou novos a cada pacote?
- [BLOCKING? nao] Valores não pessoais (nomes de grupos, linhas de pesquisa, títulos) são embedados com a Mistral na montagem, ou ficam também só na busca sem acento?
- [BLOCKING? nao] Onde mora o código da montagem (JSON → Parquet → ligações → pacote): `Etls/`, `IntegracaoBases/` ou `Oraculo/app/scripts/`?
- [BLOCKING? nao] As 4 fontes formam um contexto só ou vários (grãos diferentes: orientação, projeto, grupo, pessoa)?
- [BLOCKING? nao] Que painéis/widgets o "painel generalista" mostra por padrão, já que os de vendas saem?
- [BLOCKING? nao] O `identifier` do Tauri muda para algo com "adito"? Mais barato decidir antes do primeiro instalador.

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- 2026-11-06: usuário redefiniu IN, OUT, LATER, critérios de sucesso, restrições e assumptions (texto do usuário mantido sem alteração). O produto deixa de ser agnóstico de dados e passa a ser o painel do Campus Serra com SigPesq, Lattes, CNPq (DGP) e SRC, consultado via DuckDB sobre um pacote Parquet.
- Respostas às perguntas da rev. 1: v1 para poucos usuários com pacote entregue pela equipe; marco de pronto = critérios de sucesso acima. `identifier` continua em aberto.
- 2026-11-06 (rev. 3): (1) pacote leva ids opacos, hashes de CPF/e-mail ficam com a equipe; (2) nomes de pessoas não vão para a Mistral — removidos os embeddings de nomes, e o app tira colunas de nome do que vai ao LLM; (3) trabalho no repositório do Adito, sobre `Oraculo/app`.

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim (2026-11-06)
