from typing import Any, Dict, List
from llama_index.core.base.llms.types import ChatMessage, MessageRole

DEFAULT_INTRO_PREFERENCES = "Below are a set of relevant preferences retrieved from potentially several memory sources:"
DEFAULT_OUTRO_PREFERENCES = "This is the end of the retrieved preferences."

def convert_memory_to_system_message(response: List[Dict[str, Any]], existing_system_message: ChatMessage = None) -> ChatMessage:
    memories = [format_memory_json(memory_json) for memory_json in response]
    formatted_messages = "\n\n" + DEFAULT_INTRO_PREFERENCES + "\n"
    for memory in memories:
        formatted_messages += (
            f"\n {memory} \n\n"
        )
    formatted_messages += DEFAULT_OUTRO_PREFERENCES
    system_message = formatted_messages
    # If existing system message is available
    if existing_system_message is not None:
        system_message = existing_system_message.content.split(
            DEFAULT_INTRO_PREFERENCES
        )[0]
        system_message = system_message + formatted_messages
    return ChatMessage(content = system_message, role=MessageRole.SYSTEM)

def format_memory_json(memory_json: Dict[str, Any]) -> List[str]:
        categories = memory_json.get('categories')
        memory = memory_json.get('memory', '')
        if categories is not None:
            categories_str = ', '.join(categories)
            return f"[{categories_str}] : {memory}"
        return f"{memory}"