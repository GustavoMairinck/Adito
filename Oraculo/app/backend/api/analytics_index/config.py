import os

# As views e campos embedados vêm do embed_columns de cada contexto (views.json).
TEXT_EMBEDDING_BATCH_SIZE = int(os.getenv("TEXT_EMBEDDING_BATCH_SIZE", "100"))
TEXT_EMBEDDING_TOP_K = int(os.getenv("TEXT_EMBEDDING_TOP_K", "5"))
