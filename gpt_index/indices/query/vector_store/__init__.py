"""Query classes for vector store indices."""

from gpt_index.indices.query.vector_store.faiss import GPTFaissIndexQuery
from gpt_index.indices.query.vector_store.simple import GPTSimpleVectorIndexQuery
from gpt_index.indices.query.vector_store.weaviate import GPTWewaviateIndexQuery

__all__ = ["GPTFaissIndexQuery", "GPTSimpleVectorIndexQuery", GPTWewaviateIndexQuery]
