# User Story: [US-ETL-08] Exportar tabelas das views de fatos do PostgreSQL em JSON

**Epic:** EPIC-07 — ETL do Adito  
**Prioridade:** Alta  
**Story Points:** 5  
**Sprint:** —  
**Status:** 🔍 Review  
**Requisitos:** FR14, FR15, FR16, FR17, FR18, FR19, FR20, BR07, BR08, BR09, BR10, NFR07, NFR08, NFR09, NFR10, A06, A07 (`docs/requirements/adito-etl.md`)  
**Nível ScrumAIDev:** 1

---

## 📖 História

**Como** membro da equipe de dados  
**Eu quero** exportar do banco PostgreSQL `unificado` (somente leitura) um arquivo JSON por tabela e um `manifesto.json` para as 41 tabelas usadas pela proposta de fatos (`Docs/Fatos/PropostaFatos.md`)  
**Para que** o pacote do DuckDB possa recriar as tabelas e as 6 views analíticas (`vfact_*_resolved`) no destino sem adivinhar tipos/chaves e sem depender de um servidor PostgreSQL

### Contexto Adicional
O PostgreSQL continua sendo a base relacional oficial em 3FN (`schema unificado`, populado por `Adito/scripts/popular_banco.py`). O script `Adito/scripts/exportar_json.py` atua como ponte entre o PostgreSQL e o DuckDB: lê as 41 tabelas em uma única transação `REPEATABLE READ READ ONLY` encerrada com `ROLLBACK`, gera `<saida>/<tabela>.json` + `<saida>/manifesto.json`, confere `.gitignore`, varre CPF/e-mail e valida contagens, colunas e integridade referencial.

### Pontos de Esclarecimento
Nenhum ponto pendente (`[PRECISA CLARIFICAR]` = 0).

---

## ✅ Critérios de Aceitação

- [x] **CA1:** `python3 Adito/scripts/exportar_json.py` aceita `--saida` (padrão `Adito/etl/saida/json/`), `--modo docker|conexao` (padrão `docker`), `--servico`, `--banco`, `--usuario`, `--tabelas a,b,c`, `--forcar` e `--so-validar <pasta>`, com `--help` em português.
- [x] **CA2:** A constante no código agrupa por view as **41 tabelas** da proposta (`Docs/Fatos/PropostaFatos.md`, commit `c91761a`), recusando qualquer nome passado em `--tabelas` fora dessa lista e falhando sem criar nada se alguma tabela não existir no schema `unificado` ou se o banco estiver vazio.
- [x] **CA3:** Toda leitura ocorre em uma única sessão do `psql` dentro de `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;` encerrada com `ROLLBACK;`, e o código-fonte não contém nenhum comando `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY ... FROM` ou `GRANT`.
- [x] **CA4:** Cada tabela é gerada no PostgreSQL com `coalesce(json_agg(t ORDER BY <ordem>), '[]'::json)` (ordenada pela PK descoberta em `pg_index` ou por todas as colunas na ordem da tabela quando sem PK), gravada em `<saida>/<tabela>.json` (UTF-8, escrita atômica via temporário + rename) sem corrupção de escape e validada com `json.loads`. Duas execuções seguidas sobre o mesmo banco geram `<tabela>.json` idênticos byte a byte.
- [x] **CA5:** `<saida>/manifesto.json` registra `gerado_em`, `commit`, `proposta` (`arquivo` e `commit`), `postgres` (`SHOW server_version`) e, por tabela exportada, `linhas`, `colunas` (`nome`, `tipo`, `anulavel`, `valores_enum`), `chave_primaria` e `chaves_estrangeiras` (`coluna`, `referencia`, `destino_exportado`) lidos de `pg_catalog`.
- [x] **CA6:** O script recusa gravar em pasta que não esteja ignorada pelo git (`git check-ignore -q <saida>/x.json`) ou que já contenha JSONs sem `--forcar`; após gravar, varre os JSONs contra padrões de CPF e e-mail e, se achar algum, apaga os arquivos gerados e aborta informando apenas tabela e coluna.
- [x] **CA7:** A validação final (e `--so-validar <pasta>`) verifica validade do JSON, igualdade de `linhas`, ordem exata das chaves das colunas e integridade referencial para todas as FKs com `destino_exportado: true`, listando no resumo as FKs com `destino_exportado: false` e imprimindo o resumo por tabela.
- [x] **CA8:** As 6 views de `Docs/Fatos/PropostaFatos.md` são testadas no banco dentro de `BEGIN; ...; SELECT count(*) FROM unificado.<view>; ROLLBACK;` sem deixar rastro no schema `unificado`.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:**
  - `Adito/scripts/exportar_json.py` (novo script CLI, apenas biblioteca padrão do Python).
  - `Adito/etl/tests/test_exportar_json.py` (novos testes unitários sem depender de Docker).
  - `Adito/scripts/README.md` (nova seção `"Exportar JSON para o DuckDB"`).
- **Banco de dados:** Leitura exclusiva do schema `unificado` e de `pg_catalog` (`pg_attribute`, `format_type`, `pg_index`, `pg_constraint`, `pg_enum`).

### Dependências
- [x] Banco `unificado` populado por `Adito/scripts/popular_banco.py`.
- [x] Proposta `Docs/Fatos/PropostaFatos.md` (commit `c91761a`).

### Considerações de Performance
- Volume analítico compacto (41 tabelas, dezenas de milhares de linhas no total); exportação e validação em memória concluem em poucos segundos.

---

## 🧪 Plano de Testes

### Testes Unitários (`Adito/etl/tests/test_exportar_json.py`)
- [x] Geração do SQL com ordenação pela PK, ordenação por todas as colunas quando não há PK e recusa de nome de tabela fora da constante de 41 tabelas.
- [x] Inspeção do código-fonte de `exportar_json.py` garantindo ausência de comandos SQL de escrita (`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY ... FROM`, `GRANT`).
- [x] Recusa quando a pasta de saída não é ignorada pelo git (em repositório temporário `git init`).
- [x] Detecção de CPF e de e-mail em JSON gerado (com dados sintéticos como `"Maria Exemplo"`), removendo arquivos e reportando apenas tabela/coluna.
- [x] Validador `--so-validar`: aceita conjunto sintético coerente e rejeita contagem errada, coluna faltando/fora de ordem e FK quebrada.

### Testes de Integração / Manuais no Banco Populado
- [x] Testar as 6 views `vfact_*_resolved` dentro de `BEGIN; ...; ROLLBACK;` e registrar as contagens.
- [x] Executar `python3 Adito/scripts/exportar_json.py` duas vezes seguidas (`--forcar` na segunda) e comparar `sha256sum` dos 41 `<tabela>.json`.
- [x] Conferir contagens de linhas no schema `unificado` antes e depois da execução.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Testar as 6 views de `Docs/Fatos/PropostaFatos.md` com `BEGIN; ...; ROLLBACK;` e conferir contagens do schema `unificado`
- [x] **[TASK-002]** Implementar `Adito/scripts/exportar_json.py` (CLI, leitura `REPEATABLE READ READ ONLY`, catálogo `pg_catalog`, `manifesto.json`, `.gitignore`, anti-PII e `--so-validar`)
- [x] **[TASK-003]** Criar testes unitários em `Adito/etl/tests/test_exportar_json.py` e rodar `pytest`
- [x] **[TASK-004]** Documentar a seção `"Exportar JSON para o DuckDB"` em `Adito/scripts/README.md`
- [x] **[TASK-005]** Validar reprodutibilidade (2 execuções seguidas) e estado limpo do banco e do git

---

## 📝 Notas e Comentários

- **Spec governada:** US não exige Spec (ferramenta CLI interna de exportação de dados da equipe, Nível ScrumAIDev 1).
- **Contract governado:** US não exige Contract (sem API HTTP/webhook exposto; o schema do `manifesto.json` já está especificado na própria US e em `Adito/scripts/README.md`).

---

## ✓ Definition of Done Checklist

- [x] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [x] Testes unitários passando (`pytest`)
- [x] Duas execuções seguidas gerando `<tabela>.json` idênticos
- [x] Contagens do banco `unificado` inalteradas antes e depois
- [x] Documentação atualizada em `Adito/scripts/README.md`
- [x] `git status` sem arquivos JSON ou dados pessoais
