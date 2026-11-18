-- ============================================================
-- DDL — Star Schema de Vendas (training/ddl/schema.sql)
-- Banco: PostgreSQL
-- ============================================================

-- 1. dim_tempo
CREATE TABLE IF NOT EXISTS dim_tempo (
    id_tempo  INT PRIMARY KEY,
    dia       DATE,
    semana    INT,
    mes       INT,
    trimestre INT,
    ano       INT
);

-- 2. dim_produto
CREATE TABLE IF NOT EXISTS dim_produto (
    id_produto INT PRIMARY KEY,
    produto    VARCHAR(100),
    categoria  VARCHAR(100),
    segmento   VARCHAR(100)
);

-- 3. dim_cliente
CREATE TABLE IF NOT EXISTS dim_cliente (
    id_cliente INT PRIMARY KEY,
    cliente    VARCHAR(150),
    porte      VARCHAR(50),
    setor      VARCHAR(100)
);

-- 4. dim_regiao
CREATE TABLE IF NOT EXISTS dim_regiao (
    id_regiao INT PRIMARY KEY,
    cidade    VARCHAR(100),
    estado    CHAR(2),
    regiao    VARCHAR(50)
);

-- 5. dim_canal
CREATE TABLE IF NOT EXISTS dim_canal (
    id_canal INT PRIMARY KEY,
    canal    VARCHAR(100)
);

-- 6. dim_vendedor
CREATE TABLE IF NOT EXISTS dim_vendedor (
    id_vendedor     INT PRIMARY KEY,
    nome            VARCHAR(100),
    equipe          VARCHAR(100),
    regiao_atuacao  VARCHAR(50)
);

-- 7. fact_vendas (tabela fato central)
CREATE TABLE IF NOT EXISTS fact_vendas (
    id_venda          INT PRIMARY KEY,

    id_tempo          INT REFERENCES dim_tempo(id_tempo),
    id_produto        INT REFERENCES dim_produto(id_produto),
    id_cliente        INT REFERENCES dim_cliente(id_cliente),
    id_regiao         INT REFERENCES dim_regiao(id_regiao),
    id_canal          INT REFERENCES dim_canal(id_canal),
    id_vendedor       INT REFERENCES dim_vendedor(id_vendedor),

    quantidade_vendida INT,
    valor_bruto        DECIMAL(12,2),
    desconto           DECIMAL(12,2),
    receita_liquida    DECIMAL(12,2),
    custo              DECIMAL(12,2),
    lucro              DECIMAL(12,2)
);

-- ============================================================
-- VIEW analítica principal — vfactvendasresolved
--
-- Consolida fact_vendas com todas as dimensões.
-- Use SEMPRE esta view para consultas analíticas.
-- Evite JOINs manuais entre fact_vendas e as dimensões.
-- ============================================================
CREATE OR REPLACE VIEW vfactvendasresolved AS
SELECT
    -- FATO
    fv.id_venda,
    fv.quantidade_vendida,
    fv.valor_bruto,
    fv.desconto,
    fv.receita_liquida,
    fv.custo,
    fv.lucro,

    -- DIM_TEMPO
    dt.dia           AS data_venda,
    dt.semana,
    dt.mes,
    dt.trimestre,
    dt.ano,

    -- DIM_PRODUTO
    dp.produto,
    dp.categoria     AS categoria_produto,
    dp.segmento      AS segmento_produto,

    -- DIM_CLIENTE
    dc.cliente,
    dc.porte         AS porte_cliente,
    dc.setor         AS setor_cliente,

    -- DIM_REGIAO
    dr.cidade,
    dr.estado,
    dr.regiao,

    -- DIM_CANAL
    dca.canal,

    -- DIM_VENDEDOR
    dv.nome          AS vendedor,
    dv.equipe        AS equipe_vendas,
    dv.regiao_atuacao AS regiao_vendedor

FROM fact_vendas fv
LEFT JOIN dim_tempo    dt  ON dt.id_tempo    = fv.id_tempo
LEFT JOIN dim_produto  dp  ON dp.id_produto  = fv.id_produto
LEFT JOIN dim_cliente  dc  ON dc.id_cliente  = fv.id_cliente
LEFT JOIN dim_regiao   dr  ON dr.id_regiao   = fv.id_regiao
LEFT JOIN dim_canal    dca ON dca.id_canal   = fv.id_canal
LEFT JOIN dim_vendedor dv  ON dv.id_vendedor = fv.id_vendedor;
