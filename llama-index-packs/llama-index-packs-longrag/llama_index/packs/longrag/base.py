import typing as t

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.schema import (
    NodeRelationship,
    QueryBundle,
    RelatedNodeInfo,
    TextNode,
    BaseNode,
    NodeWithScore,
)
from llama_index.core.vector_stores.types import (
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.indices.utils import embed_nodes
from llama_index.core.indices.query.embedding_utils import (
    get_top_k_embeddings,
)
from llama_index.core.settings import (
    Settings,
    embed_model_from_settings_or_context,
    llm_from_settings_or_context,
)
from llama_index.core.vector_stores.types import (
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.core.llama_pack.base import BaseLlamaPack
from llama_index.core.llms import LLM

DEFAULT_CHUNK_SIZE = 4096
DEFAULT_MAX_CHUNK_SIZE = 6000
DEFAULT_SMALL_CHUNK_SIZE = 512
DEFAULT_TOP_K = 8
EMBEDDINGS_FNAME = "embeddings.json"


def split_doc(chunk_size: int, documents: t.List[BaseNode]) -> t.List[TextNode]:
    """Splits documents into smaller pieces.

    Args:
        chunk_size (int): Chunk size
        documents (t.List[BaseNode]): Documents

    Returns:
        t.List[TextNode]: Smaller chunks
    """
    # split docs into tokens
    text_parser = SentenceSplitter(chunk_size=chunk_size)
    text_chunks: t.List[str] = []
    doc_idxs: t.List[int] = []
    for doc_idx, doc in enumerate(documents):
        cur_txt_chunks = text_parser.split_text(doc.text)
        text_chunks.extend(cur_txt_chunks)
        doc_idxs.extend([doc_idx] * len(cur_txt_chunks))

    # construct nodes and their relationships
    nodes: t.List[TextNode] = []
    for idx, text_chunk in enumerate(text_chunks):
        node = TextNode(text=text_chunk)
        src_doc = documents[doc_idxs[idx]]
        node.metadata = src_doc.metadata

        node.metadata["parent_node"] = src_doc.id_

        if idx != 0 and doc_idxs[idx - 1] == doc_idxs[idx]:
            nodes[idx - 1].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
                node_id=node.node_id
            )
            node.relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
                node_id=nodes[idx - 1].node_id
            )

        nodes.append(node)

    return nodes


def group_docs(
    nodes: t.List[str],
    adj: t.Dict[str, t.List[str]],
    max_group_size: int = DEFAULT_MAX_CHUNK_SIZE,
) -> t.Set[t.FrozenSet[str]]:
    """Groups documents.

    Args:
        nodes (List[str]): documents IDs
        adj (Dict[str, List[str]]): related documents for each document; id -> list of doc strings
        max_group_size (int, optional): max group size. Defaults to DEFAULT_CHUNK_SIZE.
    """
    docs = sorted(nodes, key=lambda node: len(adj[node]))
    groups = set()  # set of set of IDs
    for d in docs:
        related_groups = set()
        for r in adj[d]:
            for g in groups:
                if r in g:
                    related_groups = related_groups.union(frozenset([g]))

        gnew = {d}
        related_groupsl = sorted(related_groups, key=lambda el: len(el))
        for g in related_groupsl:
            if len(gnew) + len(g) <= max_group_size:
                gnew = gnew.union(g)
                if g in groups:
                    groups.remove(g)

        groups.add(frozenset(gnew))

    return groups


def get_grouped_docs(nodes: t.List[TextNode]) -> t.List[TextNode]:
    """Gets list of documents that are grouped.

    Args:
        nodes (t.List[TextNode]): Input list

    Returns:
        t.List[TextNode]: Output list
    """
    # node IDs
    nodes_str = [node.id_ for node in nodes]
    # maps node ID -> related node IDs based on that node's relationships
    adj: t.Dict[str, t.List[str]] = {
        node.id_: [val.node_id for val in node.relationships.values()] for node in nodes
    }
    # node ID -> node
    nodes_dict = {node.id_: node for node in nodes}

    res = group_docs(nodes_str, adj)

    ret_nodes = []
    for g in res:
        cur_node = TextNode()

        for node_id in g:
            cur_node.text += nodes_dict[node_id].text + "\n\n"
            cur_node.metadata.update(nodes_dict[node_id].metadata)

        ret_nodes.append(cur_node)

    return ret_nodes


def query(
    query: VectorStoreQuery, embeddings: t.Dict[str, t.List[float]]
) -> VectorStoreQueryResult:
    """Queries.

    Args:
        query (VectorStoreQuery): Query
        embeddings (t.Dict[str, t.List[float]]): Embeddings for docs

    Returns:
        VectorStoreQueryResult: Query result
    """
    query_embedding = query.query_embedding

    emb_list: t.List[t.List[float]] = []
    node_ids: t.List[str] = []

    for id_, emb in embeddings.items():
        node_ids.append(id_)
        emb_list.append(emb)

    top_similarities, top_ids = get_top_k_embeddings(
        query_embedding,
        embeddings=emb_list,
        embedding_ids=node_ids,
    )

    return VectorStoreQueryResult(similarities=top_similarities, ids=top_ids)


class LongRAGRetriever(BaseRetriever):
    """Long RAG Retriever."""

    def __init__(
        self,
        grouped_nodes: t.List[TextNode],
        embed_model: t.Optional[BaseEmbedding] = None,
        similarity_top_k: int = DEFAULT_TOP_K,
        small_chunk_size: int = DEFAULT_SMALL_CHUNK_SIZE,
    ) -> None:
        """Constructor.

        Args:
            grouped_nodes (t.List[TextNode]): Long retrieval units, nodes with docs grouped together based on relationships
            embed_model (BaseEmbedding, optional): Embed model. Defaults to None.
            similarity_top_k (int, optional): Similarity top k. Defaults to 8.
        """
        self._grouped_nodes = grouped_nodes
        self._grouped_nodes_dict = {node.id_: node for node in grouped_nodes}
        self._embed_model = embed_model or embed_model_from_settings_or_context(
            Settings, None
        )
        self._similarity_top_k = similarity_top_k

        # split nodes into embedding chunks
        self._small_toks = split_doc(small_chunk_size, self._grouped_nodes)
        self._small_toks_dict = {node.id_: node for node in self._small_toks}

        # get embeddings
        self._embeddings = embed_nodes(
            nodes=self._small_toks, embed_model=self._embed_model, show_progress=True
        )

    def _retrieve(self, query_bundle: QueryBundle) -> t.List[NodeWithScore]:
        # make query
        query_embedding = self._embed_model.get_query_embedding(query_bundle.query_str)
        vector_store_query = VectorStoreQuery(
            query_embedding=query_embedding, similarity_top_k=self._similarity_top_k
        )

        # query for answer
        query_res = query(vector_store_query, self._embeddings)

        # determine top parents of most similar children (these are long retrieval units)
        top_parents_set: t.Set[str] = set()
        top_parents: t.List[NodeWithScore] = []
        for id_, similarity in zip(query_res.ids, query_res.similarities):
            cur_node = self._small_toks_dict[id_]
            parent_id = cur_node.metadata["parent_node"]
            if parent_id not in top_parents_set:
                top_parents_set.add(parent_id)

                parent_node = self._grouped_nodes_dict[parent_id]
                node_with_score = NodeWithScore(node=parent_node, score=similarity)
                top_parents.append(node_with_score)

                if len(top_parents_set) >= self._similarity_top_k:
                    break

        print(len(top_parents))
        assert len(top_parents) == min(self._similarity_top_k, len(self._grouped_nodes))

        return top_parents


class LongRAGPack(BaseLlamaPack):
    """Implements Long RAG.

    This implementation is based on the following paper: https://arxiv.org/pdf/2406.15319
    """

    def __init__(
        self,
        data_dir: str,
        llm: t.Optional[LLM] = None,
        embed_model: t.Optional[BaseEmbedding] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        similarity_top_k: int = DEFAULT_TOP_K,
        small_chunk_size: int = DEFAULT_SMALL_CHUNK_SIZE,
    ):
        """Constructor.

        Args:
            data_dir (str): Data directory
            llm (t.Optional[LLM]): LLM
            embed_model(Optional[BaseEmbedding]): embed model
            chunk_size (int, optional): Splits each doc to chunk_size to demonstrate grouping. Set to -1 to disable splitting then grouping. Defaults to DEFAULT_CHUNK_SIZE.
            similarity_top_k (int, optional): Top k. Defaults to DEFAULT_TOP_K.
            small_chunk_size (int, optional): Small chunk size to split large documents into smaller embeddings of small_chunk_size. Defaults to DEFAULT_SMALL_CHUNK_SIZE.
        """
        # initialize vars
        self._data_dir = data_dir
        self._embed_model = embed_model or embed_model_from_settings_or_context(
            Settings, None
        )
        self._llm = llm or llm_from_settings_or_context(Settings, None)
        self._chunk_size = chunk_size
        self._similarity_top_k = similarity_top_k
        self._small_chunk_size = small_chunk_size

        # read docs
        docs = SimpleDirectoryReader(self._data_dir).load_data()  # read documents
        if self._chunk_size != -1:
            nodes = split_doc(
                self._chunk_size, docs
            )  # split documents into chunks of chunk_size
            grouped_nodes = get_grouped_docs(
                nodes
            )  # get list of nodes after grouping (groups are combined into one node), these are long retrieval units
        else:
            grouped_nodes = docs

        # make retriever and query engine
        self._retriever = LongRAGRetriever(
            grouped_nodes=grouped_nodes,
            embed_model=self._embed_model,
            similarity_top_k=self._similarity_top_k,
            small_chunk_size=self._small_chunk_size,
        )
        self._query_eng = RetrieverQueryEngine.from_args(self._retriever)

    def get_modules(self) -> t.Dict[str, t.Any]:
        """Get Modules."""
        return {
            "query_engine": self._query_eng,
            "llm": self._llm,
            "embed_model": self._embed_model,
            "retriever": self._retriever,
        }

    def run(self, query: str) -> t.Any:
        """Runs pipeline."""
        return self._query_eng.query(query)
