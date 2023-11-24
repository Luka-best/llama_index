import pickle

from llama_index.llms import ChatMessage, MessageRole
from llama_index.memory.chat_memory_buffer import ChatMemoryBuffer

USER_CHAT_MESSAGE = ChatMessage(role=MessageRole.USER, content="test message")
ASSISTANT_CHAT_MESSAGE = ChatMessage(role=MessageRole.ASSISTANT, content="test message")


def test_put_get() -> None:
    memory = ChatMemoryBuffer.from_defaults()

    memory.put(USER_CHAT_MESSAGE)

    assert len(memory.get()) == 1
    assert memory.get()[0].content == USER_CHAT_MESSAGE.content


def test_get_with_initial_tokens_less_than_limit() -> None:
    memory = ChatMemoryBuffer.from_defaults(token_limit=1000)

    memory.put(USER_CHAT_MESSAGE)

    assert len(memory.get()) == 1
    assert memory.get()[0].content == USER_CHAT_MESSAGE.content


def test_get_with_initial_tokens_same_as_limit() -> None:
    limit = 5
    memory = ChatMemoryBuffer.from_defaults(token_limit=limit)

    memory.put(USER_CHAT_MESSAGE)
    memory.put(ASSISTANT_CHAT_MESSAGE)

    assert len(memory.get(limit-1)) == 0


def test_set() -> None:
    memory = ChatMemoryBuffer.from_defaults(chat_history=[USER_CHAT_MESSAGE])

    memory.put(USER_CHAT_MESSAGE)

    assert len(memory.get()) == 2

    memory.set([USER_CHAT_MESSAGE])
    assert len(memory.get()) == 1


def test_max_tokens() -> None:
    memory = ChatMemoryBuffer.from_defaults(chat_history=[USER_CHAT_MESSAGE], token_limit=5)

    memory.put(USER_CHAT_MESSAGE)
    assert len(memory.get()) == 2

    # do we limit properly
    memory.put(USER_CHAT_MESSAGE)
    memory.put(USER_CHAT_MESSAGE)
    assert len(memory.get()) == 2

    # does get_all work
    assert len(memory.get_all()) == 4

    # does get return in the correct order?
    memory.put(ChatMessage(role=MessageRole.USER, content="test message2"))
    assert memory.get()[-1].content == "test message2"
    assert len(memory.get()) == 2


def test_sting_save_load() -> None:
    memory = ChatMemoryBuffer.from_defaults(chat_history=[USER_CHAT_MESSAGE], token_limit=5)

    json_str = memory.to_string()

    new_memory = ChatMemoryBuffer.from_string(json_str)

    assert len(new_memory.get()) == 1
    assert new_memory.token_limit == 5


def test_dict_save_load() -> None:
    memory = ChatMemoryBuffer.from_defaults(chat_history=[USER_CHAT_MESSAGE], token_limit=5)

    json_dict = memory.to_dict()

    new_memory = ChatMemoryBuffer.from_dict(json_dict)

    assert len(new_memory.get()) == 1
    assert new_memory.token_limit == 5


def test_pickle() -> None:
    """Unpickleable tiktoken tokenizer should be circumvented when pickling."""
    memory = ChatMemoryBuffer.from_defaults()
    bytes_ = pickle.dumps(memory)
    assert isinstance(pickle.loads(bytes_), ChatMemoryBuffer)
