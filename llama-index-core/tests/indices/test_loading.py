from pathlib import Path
from typing import List

import pytest
from llama_index.core.indices.list.base import SummaryIndex
from llama_index.core.indices.loading import (
    load_index_from_storage,
    load_indices_from_storage,
)
from llama_index.core.indices.vector_store.base import VectorStoreIndex
from llama_index.core.indices.multi_modal import MultiModalVectorStoreIndex
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.query_engine.retriever_query_engine import (
    RetrieverQueryEngine,
)
from llama_index.core.schema import BaseNode, Document, ImageDocument
from llama_index.core.service_context import ServiceContext
from llama_index.core.storage.storage_context import StorageContext


def test_load_index_from_storage_simple(
    documents: List[Document], tmp_path: Path, mock_service_context: ServiceContext
) -> None:
    # construct simple (i.e. in memory) storage context
    storage_context = StorageContext.from_defaults()

    # construct index
    index = VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=mock_service_context,
    )

    # persist storage to disk
    storage_context.persist(str(tmp_path))

    # load storage context
    new_storage_context = StorageContext.from_defaults(persist_dir=str(tmp_path))

    # load index
    new_index = load_index_from_storage(
        storage_context=new_storage_context, service_context=mock_service_context
    )

    assert index.index_id == new_index.index_id


def test_load_index_from_storage_multiple(
    nodes: List[BaseNode],
    tmp_path: Path,
    mock_service_context: ServiceContext,
) -> None:
    # construct simple (i.e. in memory) storage context
    storage_context = StorageContext.from_defaults()

    # add nodes to docstore
    storage_context.docstore.add_documents(nodes)

    # construct multiple indices
    vector_index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        service_context=mock_service_context,
    )
    vector_id = vector_index.index_id

    summary_index = SummaryIndex(
        nodes=nodes,
        storage_context=storage_context,
        service_context=mock_service_context,
    )

    list_id = summary_index.index_id

    # persist storage to disk
    storage_context.persist(str(tmp_path))

    # load storage context
    new_storage_context = StorageContext.from_defaults(persist_dir=str(tmp_path))

    # load single index should fail since there are multiple indices in index store
    with pytest.raises(ValueError):
        load_index_from_storage(
            new_storage_context, service_context=mock_service_context
        )

    # test load all indices
    indices = load_indices_from_storage(storage_context)
    index_ids = [index.index_id for index in indices]
    assert len(index_ids) == 2
    assert vector_id in index_ids
    assert list_id in index_ids

    # test load multiple indices by ids
    indices = load_indices_from_storage(storage_context, index_ids=[list_id, vector_id])
    index_ids = [index.index_id for index in indices]
    assert len(index_ids) == 2
    assert vector_id in index_ids
    assert list_id in index_ids


def test_load_index_from_storage_retrieval_result_identical(
    documents: List[Document],
    tmp_path: Path,
    mock_service_context: ServiceContext,
) -> None:
    # construct simple (i.e. in memory) storage context
    storage_context = StorageContext.from_defaults()

    # construct index
    index = VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=mock_service_context,
    )

    nodes = index.as_retriever().retrieve("test query str")

    # persist storage to disk
    storage_context.persist(str(tmp_path))

    # load storage context
    new_storage_context = StorageContext.from_defaults(persist_dir=str(tmp_path))

    # load index
    new_index = load_index_from_storage(
        new_storage_context, service_context=mock_service_context
    )

    new_nodes = new_index.as_retriever().retrieve("test query str")

    assert nodes == new_nodes


def is_clip_available() -> bool:
    try:
        from llama_index.embeddings.clip import (
            ClipEmbedding,  # noqa: F401  # pants: no-infer-dep
        )

        return True
    except ImportError:
        return False


def test_load_index_from_storage_multimodal_retrieval_result_identical(
    documents: List[Document],
    image_documents: List[ImageDocument],
    tmp_path: Path,
) -> None:
    if not is_clip_available():
        pytest.skip("CLIP is not available")

    storage_context = StorageContext.from_defaults(
        vector_store=SimpleVectorStore(),
        image_store=SimpleVectorStore(),
    )

    # construct index
    index = MultiModalVectorStoreIndex.from_documents(
        documents=[*documents, *image_documents],
        storage_context=storage_context,
    )
    retriever = index.as_retriever()

    query_str = "test query str"
    query_image = image_documents[0].image_path
    assert query_image is not None

    text_nodes = retriever.retrieve(query_str)
    assert len(text_nodes) > 0

    image_nodes = retriever.image_to_image_retrieve(query_image)
    assert len(image_nodes) > 0

    # persist storage to disk
    storage_context.persist(str(tmp_path))

    # load storage context
    new_storage_context = StorageContext.from_defaults(persist_dir=str(tmp_path))

    # load index
    new_index = load_index_from_storage(new_storage_context)
    assert isinstance(new_index, MultiModalVectorStoreIndex)
    new_retriever = new_index.as_retriever()

    new_text_nodes = new_retriever.retrieve(query_str)
    new_image_nodes = new_retriever.image_to_image_retrieve(query_image)

    assert text_nodes == new_text_nodes
    assert image_nodes == new_image_nodes


def test_load_index_query_engine_service_context(
    documents: List[Document],
    tmp_path: Path,
    mock_service_context: ServiceContext,
) -> None:
    # construct simple (i.e. in memory) storage context
    storage_context = StorageContext.from_defaults()

    # construct index
    index = VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=mock_service_context,
    )

    # persist storage to disk
    storage_context.persist(str(tmp_path))

    # load storage context
    new_storage_context = StorageContext.from_defaults(persist_dir=str(tmp_path))

    # load index
    new_index = load_index_from_storage(
        storage_context=new_storage_context, service_context=mock_service_context
    )

    query_engine = index.as_query_engine()
    new_query_engine = new_index.as_query_engine()

    # make types happy
    assert isinstance(query_engine, RetrieverQueryEngine)
    assert isinstance(new_query_engine, RetrieverQueryEngine)
    # Ensure that the loaded index will end up querying with the same service_context
    assert new_query_engine._response_synthesizer._llm == mock_service_context.llm
