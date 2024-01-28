"""Retrieval evaluators."""

from typing import Any, List, Optional, Sequence, Tuple

from llama_index.bridge.pydantic import Field
from llama_index.core.base_retriever import BaseRetriever
from llama_index.evaluation.retrieval.base import (
    BaseRetrievalEvaluator,
    RetrievalEvalMode,
)
from llama_index.evaluation.retrieval.metrics_base import (
    BaseRetrievalMetric,
)
from llama_index.indices.base_retriever import BaseRetriever
from llama_index.postprocessor.types import BaseNodePostprocessor
from llama_index.schema import ImageNode, TextNode


class RetrieverEvaluator(BaseRetrievalEvaluator):
    """Retriever evaluator.

    This module will evaluate a retriever using a set of metrics.

    Args:
        metrics (List[BaseRetrievalMetric]): Sequence of metrics to evaluate
        retriever: Retriever to evaluate.
        post_processor (Optional[BaseNodePostprocessor]): Post-processor to apply after retrieval.


    """

    retriever: BaseRetriever = Field(..., description="Retriever to evaluate")
    post_processor: Optional[BaseNodePostprocessor] = Field(
        default=None, description="Optional post-processor"
    )

    def __init__(
        self,
        metrics: Sequence[BaseRetrievalMetric],
        retriever: BaseRetriever,
        post_processor: Optional[BaseNodePostprocessor] = None,
        **kwargs: Any,
    ) -> None:
        """Init params."""
        super().__init__(metrics=metrics, retriever=retriever, **kwargs)

        if "post_processor" in kwargs:
            self.post_processor = kwargs["post_processor"]
        else:
            self.post_processor = post_processor

    async def _aget_retrieved_ids_and_texts(
        self, query: str, mode: RetrievalEvalMode = RetrievalEvalMode.TEXT
    ) -> Tuple[List[str], List[str]]:
        """Get retrieved ids and texts, potentially applying a post-processor."""
        retrieved_nodes = await self.retriever.aretrieve(query)

        if self.post_processor:
            retrieved_nodes = self.post_processor.postprocess_nodes(
                retrieved_nodes, query_str=query
            )

        return (
            [node.node.node_id for node in retrieved_nodes],
            [node.node.text for node in retrieved_nodes],
        )


class MultiModalRetrieverEvaluator(BaseRetrievalEvaluator):
    """Retriever evaluator.

    This module will evaluate a retriever using a set of metrics.

    Args:
        metrics (List[BaseRetrievalMetric]): Sequence of metrics to evaluate
        retriever: Retriever to evaluate.
        post_processor (Optional[BaseNodePostprocessor]): Post-processor to apply after retrieval.

    """

    retriever: BaseRetriever = Field(..., description="Retriever to evaluate")
    post_processor: Optional[BaseNodePostprocessor] = Field(
        default=None, description="Optional post-processor"
    )

    def __init__(
        self,
        metrics: Sequence[BaseRetrievalMetric],
        retriever: BaseRetriever,
        post_processor: Optional[BaseNodePostprocessor] = None,
        **kwargs: Any,
    ) -> None:
        """Init params."""
        super().__init__(metrics=metrics, retriever=retriever, **kwargs)
        self.retriever = retriever
        self.post_processor = post_processor

    async def _aget_retrieved_ids_texts(
        self, query: str, mode: RetrievalEvalMode = RetrievalEvalMode.TEXT
    ) -> Tuple[List[str], List[str]]:
        """Get retrieved ids."""
        retrieved_nodes = await self.retriever.aretrieve(query)
        image_nodes: List[ImageNode] = []
        text_nodes: List[TextNode] = []

        if self.post_processor:
            retrieved_nodes = self.post_processor.postprocess_nodes(
                retrieved_nodes, query_str=query
            )

        for scored_node in retrieved_nodes:
            node = scored_node.node
            if isinstance(node, ImageNode):
                image_nodes.append(node)
            if node.text:
                text_nodes.append(node)

        if mode == "text":
            return (
                [node.node_id for node in text_nodes],
                [node.text for node in text_nodes],
            )
        elif mode == "image":
            return (
                [node.node_id for node in image_nodes],
                [node.text for node in image_nodes],
            )
        else:
            raise ValueError("Unsupported mode.")
