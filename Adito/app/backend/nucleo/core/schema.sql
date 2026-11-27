-- Esquema do app.db (versão 4). Bancos antigos chegam aqui pela migração em core/schema.py.

CREATE TABLE IF NOT EXISTS "core_tenant" ("id" char(32) NOT NULL PRIMARY KEY, "name" varchar(255) NOT NULL, "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL);

CREATE TABLE IF NOT EXISTS "core_user" ("id" char(32) NOT NULL PRIMARY KEY, "username" varchar(150) NOT NULL UNIQUE, "first_name" varchar(150) NOT NULL, "last_name" varchar(150) NOT NULL, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "tenant_id" char(32) NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "core_user_tenant_id_8a6e30cc" ON "core_user" ("tenant_id");

CREATE TABLE IF NOT EXISTS "core_contexto" ("id" char(32) NOT NULL PRIMARY KEY, "slug" varchar(100) NOT NULL, "name" varchar(255) NOT NULL, "description" text NOT NULL, "views" text NOT NULL CHECK ((JSON_VALID("views") OR "views" IS NULL)), "rules" text NOT NULL, "llm_row_limit" integer unsigned NULL CHECK ("llm_row_limit" >= 0), "is_active" bool NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "uniq_contexto_tenant_slug" UNIQUE ("tenant_id", "slug"));
CREATE INDEX IF NOT EXISTS "core_contexto_slug_353583bb" ON "core_contexto" ("slug");
CREATE INDEX IF NOT EXISTS "core_contexto_tenant_id_36446296" ON "core_contexto" ("tenant_id");

CREATE TABLE IF NOT EXISTS "analytics_text_embedding" ("id" char(32) NOT NULL PRIMARY KEY, "source_table" varchar(128) NOT NULL, "embedding_text" text NOT NULL, "payload_json" text NOT NULL CHECK ((JSON_VALID("payload_json") OR "payload_json" IS NULL)), "value_hash" varchar(64) NOT NULL, "embedding" BLOB NULL, "embedding_provider" varchar(50) NULL, "embedding_model" varchar(120) NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "contexto_id" char(32) NOT NULL REFERENCES "core_contexto" ("id") DEFERRABLE INITIALLY DEFERRED, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "uniq_analytics_text_embedding_value" UNIQUE ("contexto_id", "source_table", "value_hash"));
CREATE INDEX IF NOT EXISTS "analytics_text_embedding_contexto_id_e815e2a7" ON "analytics_text_embedding" ("contexto_id");
CREATE INDEX IF NOT EXISTS "analytics_text_embedding_tenant_id_3cbc327b" ON "analytics_text_embedding" ("tenant_id");
CREATE INDEX IF NOT EXISTS "ate_contexto_table_idx" ON "analytics_text_embedding" ("contexto_id", "source_table");

CREATE TABLE IF NOT EXISTS "chat_conversation" ("id" char(32) NOT NULL PRIMARY KEY, "title" varchar(255) NOT NULL, "is_pinned" bool NOT NULL DEFAULT 0, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "contexto_id" char(32) NULL REFERENCES "core_contexto" ("id") DEFERRABLE INITIALLY DEFERRED, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "chat_conversation_contexto_id_bd6b437e" ON "chat_conversation" ("contexto_id");
CREATE INDEX IF NOT EXISTS "chat_conversation_tenant_id_613bd5cb" ON "chat_conversation" ("tenant_id");
CREATE INDEX IF NOT EXISTS "chat_conversation_user_id_15357b84" ON "chat_conversation" ("user_id");

CREATE TABLE IF NOT EXISTS "chat_message" ("id" char(32) NOT NULL PRIMARY KEY, "role" varchar(20) NOT NULL, "content" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "created_at" datetime NOT NULL, "conversation_id" char(32) NOT NULL REFERENCES "chat_conversation" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "chat_message_conversation_id_a1207bf4" ON "chat_message" ("conversation_id");

CREATE TABLE IF NOT EXISTS "chat_queryexecution" ("id" char(32) NOT NULL PRIMARY KEY, "question_original" text NOT NULL, "generated_sql" text NOT NULL, "is_valid" bool NOT NULL, "error_message" text NULL, "execution_time_ms" integer NULL, "created_at" datetime NOT NULL, "contexto_id" char(32) NULL REFERENCES "core_contexto" ("id") DEFERRABLE INITIALLY DEFERRED, "message_id" char(32) NULL REFERENCES "chat_message" ("id") DEFERRABLE INITIALLY DEFERRED, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" char(32) NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "chat_queryexecution_contexto_id_d3206768" ON "chat_queryexecution" ("contexto_id");
CREATE INDEX IF NOT EXISTS "chat_queryexecution_message_id_b4ba4b6e" ON "chat_queryexecution" ("message_id");
CREATE INDEX IF NOT EXISTS "chat_queryexecution_tenant_id_b39da318" ON "chat_queryexecution" ("tenant_id");
CREATE INDEX IF NOT EXISTS "chat_queryexecution_user_id_94faad09" ON "chat_queryexecution" ("user_id");

CREATE TABLE IF NOT EXISTS "dashboard_dashboard" ("id" char(32) NOT NULL PRIMARY KEY, "name" varchar(255) NOT NULL, "description" text NOT NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" char(32) NOT NULL REFERENCES "core_user" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "dashboard_dashboard_tenant_id_524fe262" ON "dashboard_dashboard" ("tenant_id");
CREATE INDEX IF NOT EXISTS "dashboard_dashboard_user_id_81d35748" ON "dashboard_dashboard" ("user_id");

CREATE TABLE IF NOT EXISTS "dashboard_widget" ("id" char(32) NOT NULL PRIMARY KEY, "title" varchar(255) NOT NULL, "question_original" text NOT NULL, "sql_validated" text NOT NULL, "chart_type" varchar(50) NOT NULL, "mode" varchar(50) NOT NULL, "cache_ttl_hours" integer NOT NULL, "size" varchar(50) NOT NULL, "grid_x" integer NOT NULL, "grid_y" integer NOT NULL, "grid_w" integer NOT NULL, "grid_h" integer NOT NULL, "limit_rows" integer NOT NULL, "sort_order" varchar(50) NOT NULL, "status" varchar(50) NOT NULL, "last_executed_at" datetime NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "contexto_id" char(32) NULL REFERENCES "core_contexto" ("id") DEFERRABLE INITIALLY DEFERRED, "dashboard_id" char(32) NOT NULL REFERENCES "dashboard_dashboard" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "dashboard_widget_contexto_id_767d1c96" ON "dashboard_widget" ("contexto_id");
CREATE INDEX IF NOT EXISTS "dashboard_widget_dashboard_id_d8c3f7af" ON "dashboard_widget" ("dashboard_id");

CREATE TABLE IF NOT EXISTS "knowledge_knowledgeitem" ("id" char(32) NOT NULL PRIMARY KEY, "item_type" varchar(50) NOT NULL, "content" text NOT NULL, "metadata" text NOT NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "embedding" BLOB NULL, "created_at" datetime NOT NULL, "updated_at" datetime NOT NULL, "contexto_id" char(32) NULL REFERENCES "core_contexto" ("id") DEFERRABLE INITIALLY DEFERRED, "tenant_id" char(32) NOT NULL REFERENCES "core_tenant" ("id") DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS "knowledge_knowledgeitem_contexto_id_e3de0f95" ON "knowledge_knowledgeitem" ("contexto_id");
CREATE INDEX IF NOT EXISTS "knowledge_knowledgeitem_tenant_id_2c221b10" ON "knowledge_knowledgeitem" ("tenant_id");
CREATE INDEX IF NOT EXISTS "knowledge_k_item_ty_c6912b_idx" ON "knowledge_knowledgeitem" ("item_type");
