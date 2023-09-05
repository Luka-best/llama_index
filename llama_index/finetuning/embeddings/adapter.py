"""Sentence Transformer Finetuning Engine."""

from llama_index.embeddings.base import BaseEmbedding

from typing import Dict, Any, List, Optional

from llama_index.bridge.pydantic import BaseModel
from llama_index.schema import TextNode, MetadataMode
from llama_index.llms.openai import OpenAI
from llama_index.llms.base import LLM
from llama_index.embeddings.utils import resolve_embed_model
from llama_index.finetuning.types import BaseEmbeddingFinetuneEngine
from llama_index.finetuning.embeddings.common import EmbeddingQAFinetuneDataset
from llama_index.embeddings.base import BaseEmbedding
from llama_index.finetuning.embeddings.adapter_utils import train_model
from llama_index.embeddings.adapter import LinearLayer, LinearAdapterEmbeddingModel
from tqdm import tqdm
import uuid
import re
import json
import logging

logger = logging.getLogger(__name__)


class EmbeddingAdapterFinetuneEngine(BaseEmbeddingFinetuneEngine):
    """Embedding adapter finetune engine."""

    def __init__(
        self,
        dataset: EmbeddingQAFinetuneDataset,
        embed_model: BaseEmbedding,
        batch_size: int = 10,
        epochs: int = 1,
        device: Optional[str] = None,
        model_output_path: str = "model_output",
        verbose: bool = False,
        **train_kwargs: Any,
    ) -> None:
        """Init params."""
        self.dataset = dataset
        self.embed_model = embed_model

        # HACK: get dimension by passing text through it
        test_embedding = self.embed_model.get_text_embedding("hello world")
        self.dim = len(test_embedding)

        # load in data, run embedding model, define data loader

        self.batch_size = batch_size
        self.loader = self._get_data_loader(dataset)

        import torch
        from sentence_transformers import SentenceTransformer

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Use pytorch device: {}".format(device))
        self._target_device = torch.device(device)
        self.model = LinearLayer(self.dim, self.dim)

        self._model_output_path = model_output_path
        self._epochs = epochs
        self._warmup_steps = int(len(self.loader) * epochs * 0.1)
        self._train_kwargs = train_kwargs

        self._verbose = verbose

    def smart_batching_collate(self, batch: List) -> None:
        """Smart batching collate."""
        from torch import Tensor
        import torch

        query_embeddings: List[Tensor] = []
        text_embeddings: List[Tensor] = []

        for query, text in batch:
            query_embedding = self.embed_model.get_query_embedding(query)
            text_embedding = self.embed_model.get_text_embedding(text)
            # query_embeddings.append(query_embedding)
            # text_embeddings.append(text_embedding)
            # print(type(query_embedding))
            # print(type(text_embedding))
            # print(query_embedding)
            # print(text_embedding)
            # raise Exception

            query_embeddings.append(torch.tensor(query_embedding))
            text_embeddings.append(torch.tensor(text_embedding))

        query_embeddings_t = torch.stack(query_embeddings)
        text_embeddings_t = torch.stack(text_embeddings)

        return query_embeddings_t, text_embeddings_t

    def _get_data_loader(self, dataset: EmbeddingQAFinetuneDataset) -> Any:
        """Get data loader."""
        from torch.utils.data import DataLoader
        import torch

        examples: Any = []

        for query_id, query in dataset.queries.items():
            node_id = dataset.relevant_docs[query_id][0]
            text = dataset.corpus[node_id]

            examples.append((query, text))

            # query_embedding = self.embed_model.get_query_embedding(query)
            # text_embedding = self.embed_model.get_text_embedding(text)

            # query_embedding_t = torch.tensor(query_embedding)
            # text_embedding_t = torch.tensor(text_embedding)

            # examples.append((query_embedding_t, text_embedding_t))

            # # TMP
            # break

        data_loader = DataLoader(examples, batch_size=self.batch_size)
        data_loader.collate_fn = self.smart_batching_collate

        return data_loader

    def finetune(self, **train_kwargs: Any) -> None:
        """Finetune."""
        # call model training
        train_model(
            self.model,
            self.loader,
            self._target_device,
            epochs=self._epochs,
            output_path=self._model_output_path,
            warmup_steps=self._warmup_steps,
            verbose=self._verbose,
            **self._train_kwargs,
        )

        pass

    def get_finetuned_model(self, **model_kwargs: Any) -> BaseEmbedding:
        """Get finetuned model."""

        return LinearAdapterEmbeddingModel(self.embed_model, self._model_output_path)
