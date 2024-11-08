import base64
import logging
from typing import List, Sequence

import requests

from llama_index.core.schema import ImageDocument

logger = logging.getLogger(__name__)


def load_image_urls(image_urls: List[str]) -> List[ImageDocument]:
    """Convert a list of image URLs into ImageDocument objects.

    Args:
        image_urls (List[str]): List of strings containing valid image URLs.

    Returns:
        List[ImageDocument]: List of ImageDocument objects.
    """
    return [ImageDocument(image_url=url) for url in image_urls]


def encode_image(image_path: str) -> str:
    """Create base64 representation of an image.

    Args:
        image_path (str): Path to the image file

    Returns:
        str: Base64 encoded string of the image

    Raises:
        FileNotFoundError: If the `image_path` doesn't exist.
        IOError: If there's an error reading the file.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def image_documents_to_base64(
    image_documents: Sequence[ImageDocument],
) -> List[str]:
    """Convert ImageDocument objects to base64-encoded strings.

    Args:
        image_documents (Sequence[ImageDocument]: Sequence of
            ImageDocument objects

    Returns:
        List[str]: List of base64-encoded image strings
    """
    image_encodings = []

    # Encode image documents to base64
    for image_document in image_documents:
        if image_document.image:  # This field is already base64-encoded
            image_encodings.append(image_document.image)
        elif (
            image_document.image_path
        ):  # This field is a path to the image, which is then encoded.
            image_encodings.append(encode_image(image_document.image_path))
        elif (
            "file_path" in image_document.metadata
            and image_document.metadata["file_path"] != ""
        ):  # Alternative path to the image, which is then encoded.
            image_encodings.append(encode_image(image_document.metadata["file_path"]))
        elif image_document.image_url:  # Image can also be pulled from the URL.
            response = requests.get(image_document.image_url)
            try:
                image_encodings.append(
                    base64.b64encode(response.content).decode("utf-8")
                )
            except Exception as e:
                logger.warning(f"Cannot encode the image pulled from URL -> {e}")
    return image_encodings
