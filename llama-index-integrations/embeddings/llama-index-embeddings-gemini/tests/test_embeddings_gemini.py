from llama_index.core.embeddings.base import BaseEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding


def test_embedding_class():
    emb = GeminiEmbedding()
    assert isinstance(emb, BaseEmbedding)
