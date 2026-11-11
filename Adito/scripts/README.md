# Ambiente PostgreSQL — Modelo Unificado (Oraculo)

Este diretório contém a infraestrutura em Docker e os scripts SQL para provisionar o banco de dados PostgreSQL com o schema relacional unificado extraído do modelo de classes Astah (`ModeloClassesUnificado.asta`).

---

## 🚀 Como Subir o Banco

Na raiz deste diretório (`Oraculo/scripts/`):

### 1. Inicialização Automática e Validação
```bash
./recriar_banco.sh
```
O script:
1. Carrega o `.env` (porta padrão: `5435`).
2. Sobe o container `oraculo_postgres_unificado`.
3. Executa os scripts da pasta `sql/` na ordem correta (`00` a `99`).
4. Imprime o relatório de validação das tabelas e chaves criadas.

### 2. Ou via Docker Compose padrão
```bash
docker compose up -d
```

---

## 🔌 Conexão

| Parâmetro | Valor Padrão |
| :--- | :--- |
| **Host** | `localhost` |
| **Porta** | `5435` |
| **Database** | `oraculo_db` |
| **Usuário** | `oraculo` |
| **Senha** | `oraculo_password` |
| **Schema Padrão** | `unificado` |

Comando para conectar via `psql` direto no container:
```bash
docker compose exec -it oraculo-postgres psql -U oraculo -d oraculo_db
```

---

## 📁 Estrutura dos Scripts SQL

* `sql/00_schema.sql`: Cria o schema `unificado` e configura o `search_path`.
* `sql/01_tipos_e_dominios.sql`: Define os 17 tipos `ENUM` nativos e cria/popula as 14 tabelas de domínio.
* `sql/02_tabelas.sql`: Cria todas as tabelas de entidades de negócio, aplicando herança com chaves primárias e estrangeiras alinhadas.
* `sql/03_relacionamentos_e_juncoes.sql`: Cria classes associativas (com `id`), tabelas de junção N:N puras (sem `id`) e índices de alta performance em FKs.
* `sql/99_validacao.sql`: Consultas de auditoria (contagem de tabelas, colunas, enums e domínios).
