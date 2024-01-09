import builtins
import unittest
from typing import Any, Callable, Type
from unittest.mock import patch

import pytest
from llama_index.vector_stores.pinecone import PineconeVectorStore

original_import = builtins.__import__


class MockPineconePods:
    __version__ = "2.2.4"

    @staticmethod
    def init(api_key: str, environment: str) -> None:
        pass

    class Index:
        def __init__(self, index_name: str) -> None:
            pass

    class Pinecone:
        def __init__(self, api_key: str) -> None:
            pass

        def Index(self, index_name: str) -> None:
            pass


class MockPineconeServerless:
    __version__ = "3.0.0"

    class Pinecone:
        def __init__(self, api_key: str) -> None:
            pass

        class Index:
            def __init__(self, index_name: str) -> None:
                pass


class MockUnVersionedPineconeRelease:
    @staticmethod
    def init(api_key: str, environment: str) -> None:
        pass

    class Index:
        def __init__(self, index_name: str) -> None:
            pass


def get_version_attr_from_mock_classes(mock_class: Type[Any]) -> str:
    if not hasattr(mock_class, "__version__"):
        raise AttributeError(
            "The version of pinecone you are using does not contain necessary __version__ attribute."
        )
    return mock_class.__version__


def make_mock_import(pods_version: bool) -> Callable:
    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pinecone":
            return MockPineconePods if pods_version else MockPineconeServerless
        # type: ignore[named-defined]
        return original_import(name, *args, **kwargs)

    return mock_import


class TestPineconeVectorStore(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.pods_version = False
        global original_import  # type: ignore[name-defined]
        original_import = builtins.__import__

    def tearDown(self) -> None:
        builtins.__import__ = original_import

    def test_pods_version(self) -> None:
        self.pods_version = True
        mock_import_with_context = make_mock_import(self.pods_version)
        with patch("builtins.__import__", side_effect=mock_import_with_context):
            mocked_version = get_version_attr_from_mock_classes(MockPineconePods)
            assert mocked_version == "2.2.4"
            store = PineconeVectorStore(
                api_key="dummy_key", index_name="dummy_index", environment="dummy_env"
            )

    def test_serverless_version(self) -> None:
        self.pods_version = False
        mock_import_with_context = make_mock_import(self.pods_version)
        with patch("builtins.__import__", side_effect=mock_import_with_context):
            mock_version = get_version_attr_from_mock_classes(MockPineconeServerless)
            assert mock_version == "3.0.0"
            store = PineconeVectorStore(api_key="dummy_key", index_name="dummy_index")

    def test_unversioned_pinecone_client(self) -> None:
        with pytest.raises(
            AttributeError,
            match="The version of pinecone you are using does not contain necessary __version__ attribute.",
        ):
            get_version_attr_from_mock_classes(MockUnVersionedPineconeRelease)


if __name__ == "__main__":
    unittest.main()
