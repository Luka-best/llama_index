"""List index.

A simple data structure where LlamaIndex iterates through document chunks
in sequence in order to answer a given query.

"""

from typing import Any, Dict, Optional, Sequence, Type

from gpt_index.data_structs.data_structs import Node
from gpt_index.data_structs.data_structs_v2 import IndexList
from gpt_index.indices.base import DOCUMENTS_INPUT, BaseGPTIndex
from gpt_index.indices.node_utils import get_nodes_from_docstore
from gpt_index.indices.query.base import BaseGPTIndexQuery
from gpt_index.indices.query.list.embedding_query import GPTListIndexEmbeddingQuery
from gpt_index.indices.query.list.query import GPTListIndexQuery
from gpt_index.indices.query.schema import QueryMode
from gpt_index.langchain_helpers.chain_wrapper import LLMPredictor
from gpt_index.langchain_helpers.text_splitter import TextSplitter
from gpt_index.prompts.default_prompts import DEFAULT_TEXT_QA_PROMPT
from gpt_index.prompts.prompts import QuestionAnswerPrompt
from gpt_index.schema import BaseDocument

# This query is used to summarize the contents of the index.
GENERATE_TEXT_QUERY = "What is a concise summary of this document?"


class GPTListIndex(BaseGPTIndex[IndexList]):
    """GPT List Index.

    The list index is a simple data structure where nodes are stored in
    a sequence. During index construction, the document texts are
    chunked up, converted to nodes, and stored in a list.

    During query time, the list index iterates through the nodes
    with some optional filter parameters, and synthesizes an
    answer from all the nodes.

    Args:
        text_qa_template (Optional[QuestionAnswerPrompt]): A Question-Answer Prompt
            (see :ref:`Prompt-Templates`).
            NOTE: this is a deprecated field.

    """

    index_struct_cls = IndexList

    def __init__(
        self,
        documents: Optional[Sequence[DOCUMENTS_INPUT]] = None,
        index_struct: Optional[IndexList] = None,
        text_qa_template: Optional[QuestionAnswerPrompt] = None,
        llm_predictor: Optional[LLMPredictor] = None,
        text_splitter: Optional[TextSplitter] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize params."""
        self.text_qa_template = text_qa_template or DEFAULT_TEXT_QA_PROMPT
        super().__init__(
            documents=documents,
            index_struct=index_struct,
            llm_predictor=llm_predictor,
            text_splitter=text_splitter,
            **kwargs,
        )

    @classmethod
    def get_query_map(self) -> Dict[str, Type[BaseGPTIndexQuery]]:
        """Get query map."""
        return {
            QueryMode.DEFAULT: GPTListIndexQuery,
            QueryMode.EMBEDDING: GPTListIndexEmbeddingQuery,
        }


    def _build_index_from_nodes(
        self, nodes: Sequence[Node]
    ) -> IndexList:
        """Build the index from documents.

        Args:
            documents (List[BaseDocument]): A list of documents.

        Returns:
            IndexList: The created list index.
        """
        index_struct = IndexList()
        for n in nodes:
            index_struct.add_node(n)
            self._docstore.add_documents([n])
        return index_struct

    def _insert(self, document: BaseDocument, **insert_kwargs: Any) -> None:
        """Insert a document."""
        nodes = self._get_nodes_from_document(document)
        for n in nodes:
            self._index_struct.add_node(n)
            self._docstore.add_documents([n])

    def _delete(self, doc_id: str, **delete_kwargs: Any) -> None:
        """Delete a document."""
        cur_node_ids = self._index_struct.nodes
        cur_nodes = get_nodes_from_docstore(self._docstore, cur_node_ids)
        nodes_to_keep = [n for n in cur_nodes if n.ref_doc_id != doc_id]
        self._index_struct.nodes = [n.get_doc_id() for n in nodes_to_keep]

    def _preprocess_query(self, mode: QueryMode, query_kwargs: Any) -> None:
        """Preprocess query."""
        super()._preprocess_query(mode, query_kwargs)
        if "text_qa_template" not in query_kwargs:
            query_kwargs["text_qa_template"] = self.text_qa_template
