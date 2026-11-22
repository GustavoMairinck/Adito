# Especificação — Identidade Adito

Decisão: [ADR-0008](../../../Docs/ADR/ADR-0008-volta-ao-nome-adito.md), que substitui o [ADR-0005](../../../Docs/ADR/ADR-0005-nome-muninn.md). Os nomes antigos aparecem aqui de propósito, para registrar o que mudou.

## Mapa de nomes

| Onde | Muninn (ADR-0005) | Agora |
|---|---|---|
| Pasta do produto | `Muninn/` | `Adito/` |
| Identifier Tauri (pasta de dados, cofre do SO) | `br.edu.ifes.leds.muninn` | `br.edu.ifes.leds.adito` |
| Janela / productName | Muninn | Adito |
| Crate Rust / lib | `muninn` / `muninn_lib` | `adito` / `adito_lib` |
| Sidecar empacotado | `muninn-backend` | `adito-backend` |
| Pacote e CLI do ETL | `muninn_etl` / `muninn-etl` | `adito_etl` / `adito-etl` |
| Pacote npm do front | `muninn-frontend` | `adito-frontend` |
| Logos | `public/brand/muninn-*.png` | `public/brand/adito-*.png` (mesma arte) |
| Persona dos agentes | "Muninn" | "Adito", pesquisa e extensão do IFES |

Antes do Muninn, o identifier era `br.edu.ifes.leds.oraculo-esx` e as variáveis eram `ORACULO_*`/`ADITO_*`.

## Variáveis de ambiente (sem fallback)

| Muninn | Agora |
|---|---|
| `MUNINN_DATA_DIR` | `ADITO_DATA_DIR` |
| `MUNINN_APP_DB` | `ADITO_APP_DB` |
| `MUNINN_DADOS_DB` | `ADITO_DADOS_DB` |
| `MUNINN_PYTHON` | `ADITO_PYTHON` |
| `MUNINN_CHECKPOINT_DB` | `ADITO_CHECKPOINT_DB` |
| `MUNINN_LOCAL_TOKEN` | `ADITO_LOCAL_TOKEN` |
| `MUNINN_FORCE_X11` | `ADITO_FORCE_X11` |
| `MUNINN_CREDENCIAIS`, `MUNINN_DB_PATH`, `MUNINN_ETL_BASE`, `MUNINN_ETL_DIR`, `MUNINN_LOG_LEVEL` | `ADITO_CREDENCIAIS`, `ADITO_DB_PATH`, `ADITO_ETL_BASE`, `ADITO_ETL_DIR`, `ADITO_LOG_LEVEL` |

Os nomes `MUNINN_*` e `ORACULO_*` deixam de ser lidos. Quem tem `.env` ou script local precisa trocar.

## Migração no primeiro start

1. **Pasta de dados** (`app.db`, `dados.db`, checkpoints, logs): se `…/br.edu.ifes.leds.adito` não existe, a pasta antiga mais recente no mesmo pai é renomeada para a nova. A ordem é `br.edu.ifes.leds.muninn` e depois `br.edu.ifes.leds.oraculo-esx`.
   - No app: `migrate_legacy_data()` no início de `run()` (`src-tauri/src/lib.rs`), antes de o WebView criar a pasta nova.
   - No núcleo pelo terminal: `core/datastore.py::data_dir()`, só quando `ADITO_DATA_DIR` não está definido.
   - Se a pasta nova já existe, nada é movido nem sobrescrito.
2. **Chave Gemini no cofre do SO:** se o serviço novo não tem chave, a primeira chave encontrada nos serviços antigos (mesma ordem) é copiada e apagada de lá (`migrate_legacy_key()`).
3. **Preferências do navegador** (`localStorage`): o contexto selecionado e o histórico local usam chaves `adito_*`. Os valores com `muninn_*` não são migrados; o usuário só precisa escolher o contexto de novo.

## Fora do escopo

- Projetos `Etls/Horizon` e `Etls/SRC`: só as menções ao nome mudaram; os `resultados/*.json` gerados ficam como estão.
- Documentos históricos: não reescritos, só com nota.
- ADR-0005: fica como registro, com status "Substituído pelo ADR-0008".
- Repositório no GitHub e arte do logo: tarefas à parte.

## Verificação

- `git grep -i muninn` só encontra o ADR-0005, as notas históricas, esta spec, o ADR-0008 e o identifier antigo usado na migração.
- Testes: `cargo test` (migração), `core/tests.py` (pasta padrão e migração), ETL, `teste_contrato.py`, `teste_stdio.py`.
