# User Story: [US-DEVEX-02] Geração Automática e Segura de `entradas/lattes.csv` no `make etl-lattes`

**Epic:** EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx)  
**GitHub Epic Issue:** [#83](https://github.com/SmartIdea-ifes-serra/Adito/issues/83)  
**GitHub US Issue:** [#83](https://github.com/SmartIdea-ifes-serra/Adito/issues/83)  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 2  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** YES (alvo `make etl-lattes` passa a garantir a criação de `entradas/lattes.csv` quando ausente)

---

## Historia

**Como** desenvolvedor configurando o Muninn em um ambiente recém-clonado,  
**Eu quero** que `make etl-lattes` gere automaticamente `Muninn/etl/entradas/lattes.csv` quando o arquivo ainda não existir,  
**Para que** o extrator Lattes funcione sem falhar com `FileNotFoundError`, respeitando listas customizadas e mantendo dados pessoais fora do Git.

### Contexto Adicional
A pasta `Muninn/etl/entradas/` está no `.gitignore` por política anti-PII. Em ambientes limpos, `make etl-lattes` falha imediatamente com `FileNotFoundError` ao tentar ler `entradas/lattes.csv`. O mapeamento oficial `ROSTER_IDS` (93 docentes do Campus Serra com IDs Lattes de 16 dígitos) já existe em `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py`.

### Pontos de Esclarecimento
Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **CA01 (Script auxiliar `gerar_lista_lattes.py`):** Criar `Muninn/scripts/gerar_lista_lattes.py` (Python stdlib, usando `ast.parse` sem importar módulos do projeto legado) que extrai `ROSTER_IDS` de `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` e gera `Muninn/etl/entradas/lattes.csv` em UTF-8 com cabeçalho `nome,lattes_id` (criando o diretório `entradas/` automaticamente).
- [x] **CA02 (Idempotência / respeito a CSV customizado):** Se `Muninn/etl/entradas/lattes.csv` já existir, o script e o `Makefile` não sobrescrevem o arquivo (a menos que seja passada flag explícita `--force`).
- [x] **CA03 (Fallback claro sem fonte legada):** Se `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` não existir e o CSV alvo não existir, o script falha com exit code != 0 e mensagem clara explicando o caminho esperado (`Muninn/etl/entradas/lattes.csv`) e o formato CSV obrigatório (`nome,lattes_id`).
- [x] **CA04 (Integração no `Makefile`):** `etl-lattes` garante a criação prévia de `Muninn/etl/entradas/lattes.csv` quando ausente, sem exigir credenciais em `Muninn/etl/.env` (`BR03`).
- [x] **CA05 (Testes automatizados offline):** Testes unitários/CLI cobrindo geração a partir de fonte sintética, preservação de CSV customizado existente e erro amigável quando a fonte legada não existe.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; script operacional local e alvo do `Makefile` sem alteração de API, contrato ou schema de banco.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Automação de ambiente/CLI sem boundary de produto ou contrato externo.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Sem endpoint HTTP/RPC ou schema compartilhado.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR01`, `FR02`, `FR09`, `BR01`, `BR02`, `BR03`, `NFR01`, `NFR04`, `NFR05`, `A01`
- **Touch List preliminar:**
  - `Muninn/scripts/gerar_lista_lattes.py` (novo)
  - `Makefile`
  - `Muninn/etl/tests/test_onboarding_makefile.py` (novo, ou suíte dedicada de testes offline)
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** `Muninn/scripts/gerar_lista_lattes.py`, `Makefile` (`etl-lattes`).
- **APIs necessarias:** Nenhuma.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** Exit code `1` com mensagem orientativa caso a fonte `ROSTER_IDS` não exista e `entradas/lattes.csv` esteja ausente.

### Dependencias
- [x] Zero novas dependências externas (Python `stdlib`: `ast`, `csv`, `argparse`, `pathlib`).

### Follow-up / Evolução Prevista
- **Desacoplamento de `Etls/Horizon/`:** atualmente `gerar_lista_lattes.py` lê `ROSTER_IDS` do script legado `Etls/Horizon/Etl/src/scripts/generate_docentes_executive.py` via `ast` (com fallback claro caso o arquivo seja removido). Como follow-up futuro, migrar a fonte canônica de IDs Lattes para dentro do próprio `Muninn/` (ou manter uma geração dinâmica sem dependência de `Etls/`).

### Consideracoes de Performance
- Execução local em < 100 ms.

---

## Plano de Testes

### Testes Unitarios
- [x] Geração correta de `lattes.csv` (`nome,lattes_id`) a partir de arquivo Python contendo `ROSTER_IDS`.
- [x] Preservação integral de `lattes.csv` pré-existente sem sobrescrita.
- [x] Falha com exit code != 0 e mensagem orientativa quando a fonte legada não existe.

### Testes Manuais
- [x] Em diretório temporário isolado sem `entradas/lattes.csv`, confirmar que `gerar_lista_lattes.py` gera os 93 registros esperados e não altera o arquivo na segunda execução.
