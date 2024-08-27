from llama_index.core.base.llms.base import BaseLLM
from llama_index.llms.anthropic import Anthropic
import os


def test_text_inference_embedding_class():
    names_of_base_classes = [b.__name__ for b in Anthropic.__mro__]
    assert BaseLLM.__name__ in names_of_base_classes


def test_anthropic_through_vertex_ai():
    if os.getenv("ANTHROPIC_PROJECT_ID"):
        anthropic_llm = Anthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet@20240620"),
            region=os.getenv("ANTHROPIC_REGION", "europe-west1"),
            project_id=os.getenv("ANTHROPIC_PROJECT_ID"),
        )

        completion_response = anthropic_llm.complete(
            "Give me a recipe for banana bread"
        )

        assert isinstance(completion_response.text, str)
