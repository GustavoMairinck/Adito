# Validação do ETL do Horizon com dados mockados — issue #5

**Resultado:** a carga do Horizon no PostgreSQL funciona e grava os dados com precisão no caminho feliz. O teste usou 300 registros. **283 passaram em todas as verificações.** Os outros 17 mostram **5 defeitos** e **8 alertas** de qualidade de dado, descritos abaixo. Um dos defeitos (C5) interrompe a carga do Lattes inteira e precisa ser corrigido antes de rodar com dados de produção.

## Escopo

- **ETL validado:** pipeline PostgreSQL do Adito (`Etls/Horizon/Etl/src/core/logic/carga`, schema `ModeloLogicoHorizon.sql` com `ajustes_postgres.sql`). Foi chamado `executar_carga`, que é o mesmo núcleo de `python -m src.flows.pipelines.horizon_postgres --sem-download`.
- **Fontes:** SigPesq (grupos, projetos e bolsistas), CNPq (espelhos de grupo), Lattes (JSON do scriptLattes) e enriquecimento PJ (rodou sem documentos).
- **Ambiente:** PostgreSQL 16 local, Python 3.13. Nenhum acesso à internet: o crawler do CNPq lê os espelhos de arquivo, e o `CnpqCrawlerAdapter` real continua em uso.
- **Testes já existentes:** `tests/test_carga_*.py` contra o mesmo banco deram 100 aprovados e 2 com erro. Os 2 com erro são os testes do flow, que precisam do Prefect, e o Prefect não estava instalado no ambiente.

## Massa de dados (gerada com IA)

A massa foi gerada pelo script `gerar_mocks.py`, escrito com apoio de IA (Claude) a partir da estrutura que cada carregador lê. A semente é fixa, então o mesmo comando sempre produz a mesma massa.

| Fonte | Válidos | Exceções | Total |
|---|---:|---:|---:|
| SigPesq – grupos (xlsx) | 23 | 5 | 28 |
| SigPesq – projetos (xlsx) | 61 | 16 | 77 |
| SigPesq – bolsistas (3 xlsx, 2024–2026) | 96 | 24 | 120 |
| Lattes – currículos (JSON) | 40 | 10 | 50 |
| CNPq – espelhos de grupo (JSON) | 20 | 5 | 25 |
| **Total** | **240** | **60** | **300** |

**Exceções cobertas:**
- **Nulos e vazios:** grupo sem nome, projeto sem título, título só com espaços, coordenador vazio, orientado sem nome e sem e-mail, plano sem título, bolsa sem agência, currículo sem nome, currículo sem resumo, atuação sem vínculo, formação sem instituição e sem ano, artigo sem título, sem ano e sem revista.
- **Formatos inválidos:** datas `31/02/2024`, `2024/13/45`, `2025-13-01`, `abc` e `32/13/2019`; valores `1.200,00`, `R$ 750,00` e `a definir`; campus `ES`; nível de idioma `Fluente`; data `Anterior a março de 2010`; ano numérico no lugar de texto; JSON truncado; arquivo sem ID Lattes no nome.
- **Duplicidade e casamento:** grupo repetido com caixa e acento diferentes, URL do CNPq duplicada, código de projeto repetido, linha de bolsista repetida, mesmo aluno com e-mail em maiúsculas, mesmo aluno com nome escrito de outra forma, homônimo com outro ID Lattes, mesmo artigo (DOI) em dois currículos, mesmo projeto em dois currículos, projeto e orientação do Lattes com o mesmo título de um registro do SigPesq.
- **Regras de negócio:** pareceres `Reprovado`, `Em análise`, `Não aprovado` e vazio; bolsa cancelada; projeto pai inexistente (vira pai provisório); plano que estende as datas do projeto pai; grupo citado no projeto que ainda não existe; egresso sem data de saída; espelho do CNPq indisponível.

## Como foi validado

1. **Gabarito independente.** O gerador simula as regras documentadas nas docstrings de `carga/` e grava em `gabarito.json` o estado esperado do banco para cada registro: situação, datas, organização, participantes com papel e data, grupo executor, áreas, financiadora, bolsa e valor, pai, membros de grupo, perfil, formações, vínculos, artigos e coautores. O gabarito não importa nenhum código do ETL. Nos poucos pontos em que a regra de negócio é mais clara que o código, o gabarito usa a regra de negócio, marcada como `regra: negocio`.
2. **Comparação no banco.** `validar_carga.py` lê as 33 tabelas e faz **4.411 verificações**:
   - por registro;
   - globais: contagens por tipo, pessoas duplicadas, organizações, bolsas, áreas e LGPD (e-mail só em hash);
   - sobre o relatório de pendências do próprio ETL.
3. **Teste do validador.** Três valores foram corrompidos no banco: uma situação de projeto, uma data de formação de grupo e um autor de artigo. O validador acusou os três.

## Resultado

| Fonte | Registros | OK | FALHA | ALERTA |
|---|---:|---:|---:|---:|
| SigPesq – grupos | 28 | 27 | 1 (G28) | – |
| SigPesq – projetos | 77 | 74 | 2 (P64, P13) | 1 (P69) |
| SigPesq – bolsistas | 120 | 115 | 3 (B101, B108, B109) | 2 (B110, B111) |
| CNPq – espelhos | 25 | 24 | 1 (C24) | – |
| Lattes – currículos | 50 | 43 | 2 (L49, L50) | 5 (L09, L10, L45, L46, L47) |
| **Total** | **300** | **283** | **9** | **8** |

Verificações: 4.386 OK, 15 FALHA, 10 ALERTA. P13 e C24 são registros válidos que só falharam por efeito do defeito C1.

**O que foi confirmado:**
- Os registros válidos foram gravados uma única vez, com os valores transformados corretamente:
  - situação calculada pela data;
  - recálculo das datas e da situação do projeto pai;
  - sufixo `| Orientacao …` quando o título do plano já existe;
  - casamento de pessoas por e-mail e por nome (sem acento, maiúsculas ou minúsculas, espaços extras);
  - homônimo enviado para revisão;
  - artigo e projeto compartilhados gravados uma só vez;
  - coautores casados pelo nome de citação;
  - papéis e datas dos membros do CNPq, inclusive egresso e data de saída atualizada.
- As exceções tratadas pelo ETL tiveram o efeito esperado, e as 19 pendências e 3 revisões do relatório da carga batem com o gabarito. Exemplos: linha pulada com pendência, data inválida virando nula, campus inválido indo para o IFES, grupo inexistente criado pelo projeto e pai provisório criado e reaproveitado.
- **LGPD:** todos os e-mails estão gravados em hash (`@anon.lgpd`) e nenhum aparece em nome de pessoa.
- **Banco após a carga principal:** 379 pessoas, 299 iniciativas, 845 participantes, 28 grupos, 184 membros de grupo, 9 bolsas, 112 bolsas de participante, 93 produções, 149 autorias, 44 perfis Lattes, 95 formações e 62 vínculos. Nenhuma iniciativa ficou duplicada.

## Defeitos (FALHA)

| # | Defeito | Evidência | Onde | Sugestão |
|---|---|---|---|---|
| **C5** | Um ano numérico num projeto do Lattes (`"ano_inicio": 2020` em vez de `"2020"`) **derruba a carga do Lattes inteira**. O passo `lattes_curriculos` é desfeito por completo, e as orientações do Lattes e o enriquecimento PJ não rodam. | L50: `AttributeError: 'int' object has no attribute 'isdigit'`. Execução com a sonda: 0 formações, 0 produções e 0 orientações gravadas. | `adapters/sources/lattes_parser.py:336` e `:341` (`_parse_generic_projects`) | Usar `str(...)` ou o `_to_int` que já existe no parser. Também vale chamar o parser dentro de `ctx.registro`, para que um currículo ruim não derrube os outros. |
| **C1** | Quando a fonte traz só o e-mail, **a pessoa é gravada com nome vazio**. Depois, outra pessoa só com e-mail (e diferente) é **casada com a primeira**, porque o cache tem a chave `""`. | G28: líder `(lider.semnome@ifes.mock)` vira a pessoa #34 sem nome. B101: outro aluno, com outro e-mail, vira orientando #34 e ganha a bolsa. Por efeito, #34 também entra em P13 (pai do B101) e em C24 (espelho do G28). | `person_matcher.py:177` (`match_or_create`) e `:203` (busca por nome bruto) | Não criar pessoa sem nome: registrar uma pendência "pessoa sem nome". Também ignorar a chave `""` no `_persons_cache`. |
| **C2** | O parecer **"Não aprovado" passa no filtro** e o projeto é gravado, porque o filtro procura a palavra "aprovado". | P64 foi gravado como `projeto_pesquisa`: 116 projetos, quando o esperado era 115. | `carga/iniciativas_sigpesq.py:51` (`aprovado`) e `carga/regras.py:53` | Comparar com uma lista de pareceres aprovados, ou tratar a negação ("não aprovado", "reprovado") antes. |
| **C3** | O **valor da bolsa com separador de milhar ou "R$" vira 0,00.** | B108 `1.200,00` foi gravado como 0,00. B109 `R$ 750,00` foi gravado como 0,00. | `strategies/base.py:109` (`parse_currency`) | Remover o `R$` e os pontos de milhar antes de trocar a vírgula. Valor que não for número vai para as pendências. |
| **C4** | Na formação, **o coorientador é gravado como orientador** quando a descrição só tem "Coorientador: X". A regex `Orientador:` também casa dentro de "Coorientador:". | L49: Henrique Souza Loureiro foi gravado com papel `orientador`. | `carga/lattes.py:81` (`_ORIENTADOR`) | Usar o lookbehind `(?<!co)(?<!co-)Orientador:` (com `re.IGNORECASE`), para que a regex não case dentro de "Coorientador" nem de "Co-orientador". |

## Alertas (sem regra definida e sem aviso no relatório)

1. **JSON malformado e arquivo sem ID Lattes no nome** (L45, L46) são descartados em silêncio por `ler_curriculos`. Eles não aparecem nas pendências, mas deveriam: o relatório existe para dizer "o que ficou de fora".
2. **Valor não numérico** (B111, `a definir`) foi gravado como 0,00, sem pendência.
3. **A bolsa é única por programa + financiador** (B110). Um valor diferente para a mesma bolsa (850,00 contra 700,00) é descartado sem aviso.
4. **"IFES" como agência financiadora** cria uma organização separada do "Instituto Federal do Espírito Santo".
5. **E-mails das fontes:** 39 de 137 não foram gravados. O e-mail só é gravado quando a pessoa é criada; se ela já existia e foi casada pelo nome, o e-mail novo fica só no cache.
6. **Data de fim anterior à de início** (P69) foi aceita sem pendência ou revisão.
7. **Datas e situação no Lattes:**
   - projeto com conclusão prevista para 2027 virou `concluida` (L09);
   - orientação em andamento só com `ano` recebeu esse ano como **data de fim**, embora no Lattes ele seja o início (L10).
8. **Projeto do Lattes sem integrantes** (L47) ficou sem nenhum participante, nem mesmo o dono do currículo.

## Critérios de aceitação

- [x] Massa de teste gerada com IA, com 300 registros entre caminho feliz (240) e exceções (60): nulos, formatos inválidos, duplicidades e referências quebradas.
- [x] Regras de transformação conferidas nos dados mockados, registro a registro. Corretas no caminho feliz; os defeitos C1 a C4 e os alertas estão listados acima.
- [x] Resultado final confirmado no banco esperado: as 33 tabelas do `ModeloLogicoHorizon.sql` foram conferidas contra o gabarito. A carga é precisa, com as exceções C1 a C3. **C5 impede a carga do Lattes quando o dado vem com ano numérico.**

## Como reproduzir

O kit está em `Etls/Horizon/Etl/validacao_mock/`. Veja o `README.md` do kit.

```bash
export HORIZON_DATABASE_URL=postgresql://horizon:horizon@localhost:5434/horizon
python gerar_mocks.py --saida dados
python executar_etl_mock.py --schema mock_validacao
python executar_etl_mock.py --schema mock_completa --com-sonda
python validar_carga.py
```

A lista completa das verificações está em `resultados/resultado_validacao.csv`.
