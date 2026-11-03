import os


TEXT_EMBEDDING_TABLES = {
    "vfactvendasresolved": {
        "fields": [
            "produto",
            "categoria_produto",
            "segmento_produto",
            "cliente",
            "porte_cliente",
            "setor_cliente",
            "cidade",
            "estado",
            "regiao",
            "canal",
            "vendedor",
            "equipe_vendas",
            "regiao_vendedor",
        ],
        "labels": {
            "produto": "Produto",
            "categoria_produto": "Categoria do Produto",
            "segmento_produto": "Segmento do Produto",
            "cliente": "Cliente",
            "porte_cliente": "Porte do Cliente",
            "setor_cliente": "Setor do Cliente",
            "cidade": "Cidade",
            "estado": "Estado",
            "regiao": "Região",
            "canal": "Canal",
            "vendedor": "Vendedor",
            "equipe_vendas": "Equipe de Vendas",
            "regiao_vendedor": "Região do Vendedor",
        },
        "filters": {
            "exclude_null": True,
            "exclude_blank": True,
        },
    },
}

TEXT_EMBEDDING_BATCH_SIZE = int(os.getenv("TEXT_EMBEDDING_BATCH_SIZE", "100"))
TEXT_EMBEDDING_TOP_K = int(os.getenv("TEXT_EMBEDDING_TOP_K", "5"))
