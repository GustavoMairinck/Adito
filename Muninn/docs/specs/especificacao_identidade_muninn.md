# Especificação — Identidade Muninn

Decisão: [ADR-0005](../../../Docs/ADR/ADR-0005-nome-muninn.md). Os nomes antigos aparecem aqui de propósito, para registrar o que mudou.

## Mapa de nomes

| Onde | Antes | Agora |
|---|---|---|
| Pasta do produto | `Adito/` | `Muninn/` |
| Identifier Tauri (pasta de dados, cofre do SO) | `br.edu.ifes.leds.oraculo-esx` | `br.edu.ifes.leds.muninn` |
| Janela / productName | Adito | Muninn |
| Crate Rust / lib | `oraculo-esx` / `oraculo_esx_lib` | `muninn` / `muninn_lib` |
| Sidecar empacotado | `oraculo-backend` | `muninn-backend` |
| Pacote e CLI do ETL | `adito_etl` / `adito-etl` | `muninn_etl` / `muninn-etl` |
| Pacote npm do front | `oraculo-esx-frontend` | `muninn-frontend` |
| Logos | `public/brand/adito-*.png` | `public/brand/muninn-*.png` (mesma arte) |
| Persona dos agentes | "ORACULO-ESX", dados de vendas | "Muninn", pesquisa e extensão do IFES |

## Variáveis de ambiente (sem fallback)

| Antes | Agora |
|---|---|
| `ORACULO_DATA_DIR` | `MUNINN_DATA_DIR` |
| `ORACULO_APP_DB` | `MUNINN_APP_DB` |
| `ORACULO_DADOS_DB` | `MUNINN_DADOS_DB` |
| `ORACULO_PYTHON` | `MUNINN_PYTHON` |
| `ORACULO_CHECKPOINT_DB` | `MUNINN_CHECKPOINT_DB` |
| `ORACULO_LOCAL_TOKEN` | `MUNINN_LOCAL_TOKEN` |
| `ADITO_CREDENCIAIS`, `ADITO_DB_PATH`, `ADITO_ETL_BASE`, `ADITO_ETL_DIR`, `ADITO_LOG_LEVEL` | `MUNINN_CREDENCIAIS`, `MUNINN_DB_PATH`, `MUNINN_ETL_BASE`, `MUNINN_ETL_DIR`, `MUNINN_LOG_LEVEL` |

Os nomes antigos deixam de ser lidos. Quem tem `.env` ou script local precisa trocar.

## Migração no primeiro start

1. **Pasta de dados** (`app.db`, `dados.db`, checkpoints, logs): se `…/br.edu.ifes.leds.muninn` não existe e `…/br.edu.ifes.leds.oraculo-esx` existe no mesmo pai, a antiga é renomeada para a nova.
   - No app: `migrate_legacy_data()` no início de `run()` (`src-tauri/src/lib.rs`), antes de o WebView criar a pasta nova.
   - No núcleo pelo terminal: `core/datastore.py::data_dir()`, só quando `MUNINN_DATA_DIR` não está definido.
   - Se a pasta nova já existe, nada é movido nem sobrescrito.
2. **Chave Gemini no cofre do SO:** se o serviço novo não tem chave e o antigo tem, a chave é copiada e a antiga é apagada (`migrate_legacy_key()`).

## Fora do escopo

- Projetos `Etls/Horizon` e `Etls/SRC`: só as menções ao nome mudaram; os `resultados/*.json` gerados ficam como estão.
- Documentos históricos: não reescritos, só com nota.
- Repositório no GitHub e arte do logo: tarefas à parte.

## Verificação

- `git grep -iE "adito|oraculo"` no código vivo só encontra o identifier antigo usado na migração.
- Testes: `cargo test` (3 de migração), `core/tests.py` (pasta padrão e migração), ETL, `teste_contrato.py`, `teste_stdio.py`.
