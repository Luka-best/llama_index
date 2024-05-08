import os
from typing import List, Optional

from llama_index.core.bridge.pydantic import Field
from llama_index.core.callbacks import CBEventType, EventPayload
from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.instrumentation.events.rerank import (
    ReRankStartEvent,
    ReRankEndEvent,
)
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

dispatcher = get_dispatcher()

try:
    import dashscope
except ImportError:
    raise ImportError("DashScope requires `pip install dashscope`")


class DashScopeRerank(BaseNodePostprocessor):
    model: str = Field(description="Dashscope rerank model name.")
    top_n: int = Field(description="Top N nodes to return.")

    def __init__(
        self,
        top_n: int = 3,
        model: str = "gte-rerank",
        return_documents: bool = False,
        api_key: Optional[str] = None,
    ):
        try:
            api_key = api_key or os.environ["DASHSCOPE_API_KEY"]
        except IndexError:
            raise ValueError(
                "Must pass in dashscope api key or "
                "specify via DASHSCOPE_API_KEY environment variable "
            )

        super().__init__(top_n=top_n, model=model, return_documents=return_documents)

    @classmethod
    def class_name(cls) -> str:
        return "DashScopeRerank"

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        dispatch_event = dispatcher.get_dispatch_event()

        dispatch_event(
            ReRankStartEvent(
                model=self.model,
                top_n=self.top_n,
                query=query_bundle,
                nodes=nodes,
            )
        )

        if query_bundle is None:
            raise ValueError("Missing query bundle in extra info.")
        if len(nodes) == 0:
            return []

        with self.callback_manager.event(
            CBEventType.RERANKING,
            payload={
                EventPayload.NODES: nodes,
                EventPayload.MODEL_NAME: self.model,
                EventPayload.QUERY_STR: query_bundle.query_str,
                EventPayload.TOP_K: self.top_n,
            },
        ) as event:
            texts = [node.node.get_content() for node in nodes]
            results = dashscope.TextReRank.call(
                model=self.model,
                top_n=self.top_n,
                query=query_bundle.query_str,
                documents=texts,
            )
            new_nodes = []
            for result in results.output.results:
                new_node_with_score = NodeWithScore(
                    node=nodes[result.index].node, score=result.relevance_score
                )
                new_nodes.append(new_node_with_score)
            event.on_end(payload={EventPayload.NODES: new_nodes})

        dispatch_event(
            ReRankEndEvent(
                nodes=new_nodes,
            )
        )
        return new_nodes
