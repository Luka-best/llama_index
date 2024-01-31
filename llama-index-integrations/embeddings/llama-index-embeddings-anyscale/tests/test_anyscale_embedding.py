from llama_index.core.embeddings.base import BaseEmbedding
from llama_index.embeddings.anyscale import AnyscaleEmbedding


def test_anyscale_class():
    emb = AnyscaleEmbedding()
    assert isinstance(emb, BaseEmbedding)
