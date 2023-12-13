import typing
from typing import Union

from llama_index.llms.base import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
)
from llama_index.llms.types import MessageRole

if typing.TYPE_CHECKING:
    import google.ai.generativelanguage as glm
    import google.generativeai as genai


ROLES_TO_GEMINI = {
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "model",
}
ROLES_FROM_GEMINI = {v: k for k, v in ROLES_TO_GEMINI.items()}


def _error_if_finished_early(candidate: "glm.Candidate") -> None:  # type: ignore[name-defined] # only until release
    if (finish_reason := candidate.finish_reason) > 1:  # 1=STOP (normally)
        reason = finish_reason.name

        # Safety reasons have more detail, so include that if we can.
        if finish_reason == 3:  # 3=Safety
            relevant_safety = list(
                filter(
                    lambda sr: sr.probability > 1,  # 1=Negligible
                    candidate.safety_ratings,
                )
            )
            reason += f" {relevant_safety}"

        raise RuntimeError(f"Response was terminated early: {reason}")


def completion_from_gemini_response(
    response: Union[
        "genai.types.GenerateContentResponse",
        "genai.types.AsyncGenerateContentResponse",
    ],
) -> CompletionResponse:
    top_candidate = response.candidates[0]
    _error_if_finished_early(top_candidate)

    raw = {
        **(type(top_candidate).to_dict(top_candidate)),
        **(type(response.prompt_feedback).to_dict(response.prompt_feedback)),
    }
    return CompletionResponse(text=response.text, raw=raw)


def chat_from_gemini_response(
    response: Union[
        "genai.types.GenerateContentResponse",
        "genai.types.AsyncGenerateContentResponse",
    ],
) -> ChatResponse:
    top_candidate = response.candidates[0]
    _error_if_finished_early(top_candidate)

    raw = {
        **(type(top_candidate).to_dict(top_candidate)),
        **(type(response.prompt_feedback).to_dict(response.prompt_feedback)),
    }
    role = ROLES_FROM_GEMINI[top_candidate.content.role]
    return ChatResponse(message=ChatMessage(role=role, content=response.text), raw=raw)


def chat_message_to_gemini(message: ChatMessage) -> "genai.types.ContentDict":
    """Convert ChatMessages to Gemini-specific history, including ImageDocuments."""
    parts = [message.content]
    if images := message.additional_kwargs.get("images"):
        try:
            import PIL

            parts += [PIL.Image.open(doc.resolve_image()) for doc in images]
        except ImportError:
            # This should have been caught earlier, but tell the user anyway.
            raise ValueError("Multi-modal support requires PIL.")

    return {
        "role": ROLES_TO_GEMINI[message.role],
        "parts": parts,
    }
