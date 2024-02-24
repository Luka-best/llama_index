import logging
from typing import Dict
from octoai.chat import TextModel

TEXT_MODELS: Dict[str, int] = {
    TextModel.CODELLAMA_7B_INSTRUCT_FP16: 16384,
    TextModel.CODELLAMA_13B_INSTRUCT_FP16: 16384,
    TextModel.CODELLAMA_34B_INSTRUCT_FP16: 16384,
    TextModel.CODELLAMA_70B_INSTRUCT_FP16: 4096,
    TextModel.LLAMA_2_13B_CHAT_FP16: 4096,
    TextModel.LLAMA_2_70B_CHAT_FP16: 4096,
    TextModel.MISTRAL_7B_INSTRUCT_FP16: 32768,
    TextModel.MIXTRAL_8X7B_INSTRUCT_FP16: 32768
}

ALL_AVAILABLE_MODELS = {
    **TEXT_MODELS
}

MISSING_TOKEN_ERROR_MESSAGE = """No token found for OpenAI.
Please set the OCTOAI_TOKEN environment \
variable prior to initialization.
API keys can be found or created at \
https://octoai.cloud/settings
"""

logger = logging.getLogger(__name__)

def octoai_modelname_to_contextsize(modelname: str) -> int:
    """Calculate the maximum number of tokens possible to generate for a model.

    Args:
        modelname: The modelname we want to know the context size for.

    Returns:
        The maximum context size

    Examples:
        .. code-block:: python

            max_tokens = octoai.modelname_to_contextsize(TextModel.CODELLAMA_13B_INSTRUCT_FP16)
            max_tokens = octoai.modelname_to_contextsize("llama-2-13b-chat-fp16")
    """

    if modelname not in ALL_AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown model {modelname!r}. Please provide a supported model name as \
            a string or using the TextModels enum from the OctoAI SDK:"
            f" {', '.join(ALL_AVAILABLE_MODELS.keys())}"
        )
    return ALL_AVAILABLE_MODELS[modelname]
