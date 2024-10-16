from typing import Dict, Generator, Union
import pytest
from docker.models.containers import Container
from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store.base import BaseChatStore
from llama_index.storage.chat_store.postgres import PostgresChatStore


def test_class():
    names_of_base_classes = [b.__name__ for b in PostgresChatStore.__mro__]
    assert BaseChatStore.__name__ in names_of_base_classes


@pytest.fixture()
def postgres_kvstore(
    postgres_container: Dict[str, Union[str, Container]],
) -> Generator[PostgresChatStore, None, None]:
    chat_store = None
    try:
        chat_store = PostgresChatStore.from_uri(
            uri=postgres_container["connection_string"],
            use_jsonb=True,
        )
        yield chat_store
    finally:
        if chat_store:
            keys = chat_store.get_keys()
            for key in keys:
                chat_store.delete_messages(key)


def test_postgres_add_message(postgres_kvstore: PostgresChatStore):
    key = "test_add_key"

    message = ChatMessage(content="add_message_test", role="user")
    postgres_kvstore.add_message(key, message=message)

    result = postgres_kvstore.get_messages(key)

    assert result[0].content == "add_message_test" and result[0].role == "user"


def test_set_and_retrieve_messages(postgres_kvstore: PostgresChatStore):
    messages = [
        ChatMessage(content="First message", role="user"),
        ChatMessage(content="Second message", role="user"),
    ]
    key = "test_set_key"
    postgres_kvstore.set_messages(key, messages)

    retrieved_messages = postgres_kvstore.get_messages(key)
    assert len(retrieved_messages) == 2
    assert retrieved_messages[0].content == "First message"
    assert retrieved_messages[1].content == "Second message"


def test_delete_messages(postgres_kvstore: PostgresChatStore):
    messages = [ChatMessage(content="Message to delete", role="user")]
    key = "test_delete_key"
    postgres_kvstore.set_messages(key, messages)

    postgres_kvstore.delete_messages(key)
    retrieved_messages = postgres_kvstore.get_messages(key)
    assert retrieved_messages == []


def test_delete_specific_message(postgres_kvstore: PostgresChatStore):
    messages = [
        ChatMessage(content="Keep me", role="user"),
        ChatMessage(content="Delete me", role="user"),
    ]
    key = "test_delete_message_key"
    postgres_kvstore.set_messages(key, messages)

    postgres_kvstore.delete_message(key, 1)
    retrieved_messages = postgres_kvstore.get_messages(key)
    assert len(retrieved_messages) == 1
    assert retrieved_messages[0].content == "Keep me"


async def test_get_keys(postgres_kvstore: PostgresChatStore):
    # Add some test data
    postgres_kvstore.set_messages("key1", [ChatMessage(content="Test1", role="user")])
    postgres_kvstore.set_messages("key2", [ChatMessage(content="Test2", role="user")])

    keys = postgres_kvstore.get_keys()
    assert "key1" in keys
    assert "key2" in keys


async def test_delete_last_message(postgres_kvstore: PostgresChatStore):
    key = "test_delete_last_message"
    messages = [
        ChatMessage(content="First message", role="user"),
        ChatMessage(content="Last message", role="user"),
    ]
    postgres_kvstore.set_messages(key, messages)

    deleted_message = postgres_kvstore.delete_last_message(key)

    assert deleted_message.content == "Last message"

    remaining_messages = postgres_kvstore.get_messages(key)

    assert len(remaining_messages) == 1
    assert remaining_messages[0].content == "First message"


@pytest.mark.asyncio()
async def test_async_postgres_add_message(postgres_kvstore: PostgresChatStore):
    key = "test_async_add_key"

    message = ChatMessage(content="async_add_message_test", role="user")
    await postgres_kvstore.async_add_message(key, message=message)

    result = await postgres_kvstore.async_get_messages(key)

    assert result[0].content == "async_add_message_test" and result[0].role == "user"


@pytest.mark.asyncio()
async def test_async_set_and_retrieve_messages(postgres_kvstore: PostgresChatStore):
    messages = [
        ChatMessage(content="First async message", role="user"),
        ChatMessage(content="Second async message", role="user"),
    ]
    key = "test_async_set_key"
    await postgres_kvstore.async_set_messages(key, messages)

    retrieved_messages = await postgres_kvstore.async_get_messages(key)
    assert len(retrieved_messages) == 2
    assert retrieved_messages[0].content == "First async message"
    assert retrieved_messages[1].content == "Second async message"


@pytest.mark.asyncio()
async def test_async_delete_messages(postgres_kvstore: PostgresChatStore):
    messages = [ChatMessage(content="Async message to delete", role="user")]
    key = "test_async_delete_key"
    await postgres_kvstore.async_set_messages(key, messages)

    await postgres_kvstore.async_delete_messages(key)
    retrieved_messages = await postgres_kvstore.async_get_messages(key)
    assert retrieved_messages == []


@pytest.mark.asyncio()
async def test_async_delete_specific_message(postgres_kvstore: PostgresChatStore):
    messages = [
        ChatMessage(content="Async keep me", role="user"),
        ChatMessage(content="Async delete me", role="user"),
    ]
    key = "test_async_delete_message_key"
    await postgres_kvstore.async_set_messages(key, messages)

    await postgres_kvstore.async_delete_message(key, 1)
    retrieved_messages = await postgres_kvstore.async_get_messages(key)
    assert len(retrieved_messages) == 1
    assert retrieved_messages[0].content == "Async keep me"


@pytest.mark.asyncio()
async def test_async_get_keys(postgres_kvstore: PostgresChatStore):
    # Add some test data
    await postgres_kvstore.async_set_messages(
        "async_key1", [ChatMessage(content="Test1", role="user")]
    )
    await postgres_kvstore.async_set_messages(
        "async_key2", [ChatMessage(content="Test2", role="user")]
    )

    keys = await postgres_kvstore.aget_keys()
    assert "async_key1" in keys
    assert "async_key2" in keys


@pytest.mark.asyncio()
async def test_async_delete_last_message(postgres_kvstore: PostgresChatStore):
    key = "test_async_delete_last_message"
    messages = [
        ChatMessage(content="First async message", role="user"),
        ChatMessage(content="Last async message", role="user"),
    ]
    await postgres_kvstore.async_set_messages(key, messages)

    deleted_message = await postgres_kvstore.async_delete_last_message(key)

    assert deleted_message.content == "Last async message"

    remaining_messages = await postgres_kvstore.async_get_messages(key)

    assert len(remaining_messages) == 1
    assert remaining_messages[0].content == "First async message"
