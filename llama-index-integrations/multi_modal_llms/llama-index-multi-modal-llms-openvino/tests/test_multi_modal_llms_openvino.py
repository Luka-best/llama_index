import numpy as np
import pytest
import tempfile
import os

from PIL import Image
from unittest.mock import patch
from llama_index.core.multi_modal_llms.base import MultiModalLLM
from llama_index.multi_modal_llms.openvino import OpenVINOMultiModal


@pytest.fixture(scope="module")
def mock_model():
    with patch(
        "llama_index.multi_modal_llms.openvino.base.AutoProcessor"
    ) as mock_processor:
        mock_processor = mock_processor.from_pretrained.return_value

        yield OpenVINOMultiModal(model_id_or_path="OpenGVLab/InternVL2-2B")


# Replace the existing 'model' fixture with this mock_model
@pytest.fixture(scope="module")
def model(mock_model):
    return mock_model


@pytest.fixture(scope="module")
def temp_image_path():
    # Create a white square image
    white_square = np.ones((100, 100, 3), dtype=np.uint8) * 255
    image = Image.fromarray(white_square)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        image.save(temp_file, format="PNG")
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file after the test
    os.unlink(temp_path)


def test_class():
    names_of_base_classes = [b.__name__ for b in OpenVINOMultiModal.__mro__]
    assert MultiModalLLM.__name__ in names_of_base_classes


def test_initialization(model):
    assert isinstance(model, OpenVINOMultiModal)
    assert model.model_id_or_path == "OpenGVLab/InternVL2-2B"


def test_metadata(model):
    metadata = model.metadata
    assert metadata.model_name == "OpenGVLab/InternVL2-2B"
    assert metadata.context_window == 3900  # Default value
    assert metadata.num_output == 256  # Default value


# def test_complete(model, temp_image_path):
#     prompt = "Describe this image:"
#     image_doc = ImageDocument(image_path=temp_image_path)

#     # Mock the _prepare_messages and _generate methods
#     model._messages_to_prompt = MagicMock(return_value={"mocked": "inputs"})
#     model._generate = MagicMock(return_value="This is a mocked response.")

#     response = model.complete(prompt, image_documents=[image_doc])

#     assert response.text == "This is a mocked response."
#     model._messages_to_prompt.assert_called_once()
#     model._generate.assert_called_once_with({"mocked": "inputs"})


# def test_stream_complete(model, temp_image_path):
#     prompt = "Describe this image:"
#     image_doc = ImageDocument(image_path=temp_image_path)

#     # Mock the _prepare_messages and _generate methods
#     model._messages_to_prompt = MagicMock(return_value={"mocked": "inputs"})
#     model._generate = MagicMock(return_value="This is a mocked response.")

#     response_gen = model.stream_complete(prompt, image_documents=[image_doc])
#     response = list(response_gen)
#     assert response[-1].text == "This is a mocked response."
#     model._messages_to_prompt.assert_called_once()
#     model._generate.assert_called_once_with({"mocked": "inputs"})


# def test_chat(model, temp_image_path):
#     messages = [ChatMessage(role="user", content="What's in this image?")]
#     image_doc = ImageDocument(image_path=temp_image_path)

#     # Mock the _prepare_messages and _generate methods
#     model._prepare_messages = MagicMock(return_value={"mocked": "inputs"})
#     model._generate = MagicMock(return_value="This is a mocked chat response.")

#     response = model.chat(messages, image_documents=[image_doc])

#     assert response.message.content == "This is a mocked chat response."
#     model._prepare_messages.assert_called_once()
#     model._generate.assert_called_once_with({"mocked": "inputs"})
