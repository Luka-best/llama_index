import asyncio
from typing import Any, List, Callable

from llama_index.core.async_utils import run_jobs
from llama_index.core.indices.property_graph.utils import (
    default_parse_triplets_fn,
)
from llama_index.core.graph_stores.types import EntityNode, Relation
from llama_index.core.prompts import PromptTemplate
from llama_index.core.prompts.default_prompts import (
    DEFAULT_KG_TRIPLET_EXTRACT_PROMPT,
)
from llama_index.core.schema import TransformComponent, BaseNode
from llama_index.core.llms.llm import LLM


class SimpleLLMTripletExtractor(TransformComponent):
    """Extract triplets from a graph."""

    llm: LLM
    extract_prompt: PromptTemplate
    parse_fn: Callable
    num_workers: int
    max_triplets_per_chunk: int
    show_progress: bool

    def __init__(
        self,
        llm: LLM,
        extract_prompt: str = None,
        parse_fn: Callable = default_parse_triplets_fn,
        max_triplets_per_chunk: int = 10,
        num_workers: int = 4,
        show_progress: bool = False,
    ) -> None:
        """Init params."""
        super().__init__(
            llm=llm,
            extract_prompt=extract_prompt or DEFAULT_KG_TRIPLET_EXTRACT_PROMPT,
            parse_fn=parse_fn,
            num_workers=num_workers,
            max_triplets_per_chunk=max_triplets_per_chunk,
            show_progress=show_progress,
        )

    @classmethod
    def class_name(cls) -> str:
        return "ExtractTripletsFromText"

    def __call__(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        """Extract triplets from nodes."""
        return asyncio.run(self.acall(nodes, **kwargs))

    async def _extract(self, node: BaseNode) -> BaseNode:
        """Extract triplets from a node."""
        assert hasattr(node, "text")

        text = node.get_content(metadata_mode="llm")
        try:
            llm_response = await self.llm.apredict(
                self.extract_prompt,
                text=text,
                max_knowledge_triplets=self.max_triplets_per_chunk,
            )
            triplets = self.parse_fn(llm_response)
        except ValueError:
            triplets = []

        existing_nodes = node.metadata.pop("nodes", [])
        existing_relations = node.metadata.pop("relations", [])

        metadata = node.metadata.copy()
        for subj, rel, obj in triplets:
            subj_node = EntityNode(name=subj, properties=metadata)
            obj_node = EntityNode(name=obj, properties=metadata)
            rel_node = Relation(
                label=rel,
                source_id=subj_node.id,
                target_id=obj_node.id,
                properties=metadata,
            )

            existing_nodes.extend([subj_node, obj_node])
            existing_relations.append(rel_node)

        node.metadata["nodes"] = existing_nodes
        node.metadata["relations"] = existing_relations

        return node

    async def acall(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        """Extract triplets from nodes async."""
        jobs = []
        for node in nodes:
            jobs.append(self._extract(node))

        return await run_jobs(
            jobs, workers=self.num_workers, show_progress=self.show_progress
        )
