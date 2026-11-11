# ETL do Adito

Scripts que a equipe de dados usa para montar o pacote entregue ao usuário. O usuário do Adito nunca roda nada desta pasta.

Referências: `../docs/discovery/adito.md` (rev. 4), `../docs/requirements/adito-etl.md`, stories `../docs/stories/US-ETL-*.md`. Carga no banco unificado: `../scripts/popular_banco.py`.

## Fases

| Fase | O que faz | Comando | Status |
|---|---|---|---|
| Extração SRC (ações) | Consulta pública: lista, detalhe e vínculos de cada ação | `adito-etl src-acoes` | US-ETL-01 |
| Extração SRC (participações) | Área autenticada: público-alvo e equipe de cada atividade, sem CPF/e-mail | `adito-etl src-participacoes` | US-ETL-02 |
| Extração SigPesq | Baixa grupos, projetos e orientações e converte para JSON filtrado | `adito-etl sigpesq` | US-ETL-03 |
| Extração CNPq/DGP | Espelho de cada grupo do SigPesq (URL em `Column1`) | `adito-etl cnpq` | US-ETL-04 |
| Extração Lattes | Currículos da lista `entradas/lattes.csv` pelo `scriptLattes` | `adito-etl lattes` | US-ETL-05 |
| Cruzamento | Liga pessoas entre as fontes pelo nome (inferência do horizon) | `adito-etl cruzar` | US-ETL-06 |
| Montagem | Parquet + `abrir.sql` + `manifesto.json` | — | fora deste recorte |

## Como rodar

```bash
cd Adito/etl
python3 -m venv .venv
.venv/bin/pip install -e '.[sigpesq,cnpq,lattes,infisical,dev]' 'playwright==1.64.0'
.venv/bin/playwright install chromium   # se o navegador ainda não estiver instalado
cp .env.example .env                     # ADITO_CREDENCIAIS=infisical + INFISICAL_* (ou =env + usuário/senha)
```

```bash
.venv/bin/adito-etl src-acoes --campus Serra      # brutos/src/acoes/
.venv/bin/adito-etl src-participacoes             # brutos/src/participacoes/ (credencial do SRC)
.venv/bin/adito-etl sigpesq                       # brutos/sigpesq/ (credencial do SigPesq)
.venv/bin/adito-etl cnpq                          # brutos/cnpq/ (precisa do bruto do SigPesq)
.venv/bin/adito-etl lattes                        # brutos/lattes/ (lista em entradas/lattes.csv)
.venv/bin/adito-etl cruzar                        # trabalho/pessoas.json + relatorio_cruzamento.md
.venv/bin/adito-etl verificar-pii                 # confere brutos/ e trabalho/
.venv/bin/python -m pytest                        # testes (inclui a varredura de PII sobre os dados reais)
```

Outros comandos:
- `adito-etl src-acoes --max 3` grava só 3 ações (teste). A listagem ordena por Processo nº, é sempre em série e confere o "Total" da consulta (sem ordem fixa, a consulta repete e omite ações: 159 de 207 em paralelo, 196-197 em série, em 2026-11-10).
- `adito-etl src-participacoes --processo 23158.000000/2025-00` coleta só os processos indicados; sem `--processo`, lê `brutos/src/acoes/_index.json` e pula os já gravados (retomada).
- `adito-etl sigpesq-converter --de PASTA` converte XLSX do SigPesq já baixados (ex.: `data/raw/sigpesq` do horizon_etl), sem apagar a origem.
- `adito-etl lattes-converter --de PASTA` converte JSON do scriptLattes já gerados (ex.: `data/lattes_json` do horizon_etl), sem apagar a origem. Currículo vazio (`[Nome-nao-identificado]`) vira falha.
- `adito-etl cnpq --unidade Serra --max 3` baixa só 3 grupos da unidade Serra; grupos já gravados são pulados (use `--refazer` para baixar de novo).
- `adito-etl lattes --max 2 --workers 1` baixa só 2 currículos. Cada currículo tem `LATTES_TENTATIVAS` tentativas (padrão 2), como no horizon.

Cada extrator grava `brutos/<fonte>/_extracao.json` com início, fim, commit, contagens, falhas e avisos por etapa. Código de saída: 0 ok; 1 terminou com falhas em unidades; 2 erro que impediu a execução.

## Credenciais

`ADITO_CREDENCIAIS` no `.env` escolhe a origem, sem padrão (como o `SIGPESQ_CREDENTIALS_SOURCE` do horizon_etl):
- `infisical`: lê os segredos no Infisical com a identidade de máquina (`INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`; host, ambiente e caminho têm padrão). Segredos: `sigpesq-user`/`sigpesq-password` (os mesmos do horizon) e `src-user`/`src-password`; para usar outros nomes, defina `INFISICAL_SRC_USER_SECRET` etc. Código em `segredos.py`, portado de `horizon_etl/src/adapters/secrets/infisical.py`.
- `env`: lê `SRC_USER`/`SRC_PASSWORD` e `SIGPESQ_USER`/`SIGPESQ_PASSWORD` do `.env`.

## Dados pessoais (BR01)

Nenhuma fase guarda CPF, e-mail, telefone, fax, celular ou data de nascimento. Além do nome, entram só o endereço profissional do Lattes (sem telefone; o sexo foi aprovado, mas o scriptLattes devolve "Masculino" para todos e por isso sai) e o endereço do grupo no CNPq (decisão de 2026-11-11).
- Cada fonte tem uma **lista de colunas permitidas** (`fontes/src/participacoes.py`, `fontes/sigpesq/colunas.py`, `fontes/lattes/colunas.py`, `fontes/cnpq/grupos.py`). CPF, e-mail e celular são descartados na leitura; qualquer outra coluna fora da lista é descartada e aparece como aviso.
- Textos livres passam por `pii.sanitizar` (e-mail no resumo, "Nome (email)" na lista de líderes do SigPesq).
- `comum.gravar_json` recusa gravar JSON com CPF, e-mail, 11 dígitos seguidos ou coluna pessoal.
- Os XLSX do SigPesq (`trabalho/sigpesq_xlsx/`) e o HTML e o JSON completo do Lattes (`trabalho/lattes_*`) são apagados ao fim. Do endereço profissional do Lattes saem telefone, fax e ramal; do endereço do grupo no CNPq saem telefone, fax e e-mail de contato.

Mesmo assim, `brutos/`, `trabalho/`, `saida/`, `.env` e `*.xlsx` estão no `.gitignore` desta pasta.

## Cruzamento (US-ETL-06)

Mesma inferência por nome do horizon_etl (`person_identity.py` + `person_matcher.match_or_create` com `strict_match=True`), sempre por igualdade exata:
- Dois nomes são a mesma pessoa quando coincide (a) a forma normalizada (sem acento, minúsculo, pontuação vira espaço), (b) a forma sem partículas (da, de, dos...) e com "Jr" = "Junior", ou (c) as mesmas palavras em outra ordem ("SILVA, João" = "João Silva"). A ligação é transitiva. Filho/Neto/Sobrinho continuam distintos.
- Nome com menos de duas palavras fora títulos ("Dr", "Maria") não liga a nada; vai para o relatório.
- Homônimos: se o grupo de nomes tiver dois ids Lattes de titular diferentes, não liga (cada um vira entrada `ambiguo`).
- Nome exibido: o do titular do Lattes, se houver; senão a grafia sem vírgula, não toda em maiúsculas e mais frequente. Grafias juntadas ficam em `variantes`.
- Id da pessoa: `p_` + 16 caracteres base32 do SHA-256 da menor forma sem partículas do grupo (estável entre execuções).
- Leitores: SRC, SigPesq, Lattes (titular, integrantes de projeto, orientandos) e CNPq (líderes e recursos humanos). Pastas de outras fontes em `brutos/` aparecem como "sem leitor ainda".

## Origem do código (BR06)

Os repositórios de origem não foram alterados.

| Pasta | Origem | Commit |
|---|---|---|
| `src/adito_etl/fontes/src/` | SRCEtl (`github.com/ifesserra-lab/src`), `src/src_etl/etl/` (`scraper.py`, `detail.py`, `vinculadas.py`, `models.py`, `gerenciar.py`, partes de `pipeline.py`) | `d66fc746`; `scraper.py` da branch `fix/listagem-serial-acoes` (ordenação + conferência do total), ainda não commitada no SRCEtl |
| `src/adito_etl/fontes/sigpesq/download.py` | horizon_etl, `src/adapters/sources/sigpesq/adapter.py` (sem Infisical) | `13a1cec` |
| `src/adito_etl/fontes/cnpq/grupos.py` | horizon_etl, `src/flows/cnpq/groups.py` (validação da URL) e `src/adapters/sources/cnpq_crawler.py` | `13a1cec` |
| `src/adito_etl/fontes/lattes/download.py` | horizon_etl, `src/flows/lattes/download.py` e `core/logic/lattes_generators.py` (sem Prefect/banco; lista em `entradas/lattes.csv`, extraída da lista fixa do horizon) | `13a1cec` |
| `src/adito_etl/cruzamento/normalizar.py`, leitor do CNPq | horizon_etl, `core/logic/person_identity.py`, `person_matcher.py`, `adapters/sources/cnpq_crawler.py` (`extract_members`) | `13a1cec` |
| `src/adito_etl/segredos.py` | horizon_etl, `src/adapters/secrets/infisical.py` | `13a1cec` |
| `src/adito_etl/pii.py` | baseado em `auditar_pii` do SRCEtl (`dashboard/export_json.py`) | `d66fc746` |

Mudanças em relação ao SRCEtl: `url_detalhe` sem o `pfdlgcid` de sessão; e-mails em textos livres mascarados; participações só com as colunas permitidas; credencial em `SRC_USER`/`SRC_PASSWORD`; logout sem depender do nome do usuário.
