# [Beta] Multi-modal models

## Concept

Large language models (LLMs) are text-in, text-out. Large Multi-modal Models (LMMs) generalize this beyond the text modalities. For instance, models such as GPT-4V allow you to jointly input both images and text, and output text.

We've included a base `MultiModalLLM` abstraction to allow for text+image models. **NOTE**: This naming is subject to change!

## Usage Pattern

The following code snippet shows how you can get started using LMMs e.g. with GPT-4V.

```python
from llama_index.multi_modal_llms import OpenAIMultiModal
from llama_index.multi_modal_llms.generic_utils import (
    load_image_urls,
)
from llama_index import SimpleDirectoryReader

# load image documents from urls
image_documents = load_image_urls(image_urls)

# load image documents from local directory
image_documents = SimpleDirectoryReader(local_directory).load_data()

# non-streaming
openai_mm_llm = OpenAIMultiModal(
    model="gpt-4-vision-preview", api_key=OPENAI_API_TOKEN, max_new_tokens=300
)
response = openai_mm_llm.complete(
    prompt="what is in the image?", image_documents=image_documents
)
```

**Legend**

- ✅ = should work fine
- 🛑 = not available at the moment. Support on the way

### End to End Multi-Modal Work Flow

The tables below attempt to show the **initial** steps with various LlamaIndex features for building your own Multi-Modal RAGs. You can combine different modules/steps together for composing your own Multi-Modal RAG orchestration.

| Query Type | Data Sources<br>for MultiModal<br>Vector Store/Index | MultiModal<br>Embedding                | Retriever                                        | Query<br>Engine        | Output<br>Data<br>Type                   |
| ---------- | ---------------------------------------------------- | -------------------------------------- | ------------------------------------------------ | ---------------------- | ---------------------------------------- |
| Text ✅    | Text ✅                                              | Text ✅                                | Top-k retrieval ✅<br>Simple Fusion retrieval ✅ | Simple Query Engine ✅ | Retrieved Text ✅<br>Generated Text ✅   |
| Image ✅   | Image ✅                                             | Image ✅<br>Image to Text Embedding ✅ | Top-k retrieval ✅<br>Simple Fusion retrieval ✅ | Simple Query Engine ✅ | Retrieved Image ✅<br>Generated Image 🛑 |
| Audio 🛑   | Audio 🛑                                             | Audio 🛑                               | 🛑                                               | 🛑                     | Audio 🛑                                 |
| Video 🛑   | Video 🛑                                             | Video 🛑                               | 🛑                                               | 🛑                     | Video 🛑                                 |

### Multi-Modal LLM Models

These notebooks serve as examples how to leverage and integrate Multi-Modal LLM model, Multi-Modal embeddings, Multi-Modal vector stores, Retriever, Query engine for composing Multi-Modal RAG orchestration.

| Multi-Modal<br>Vision Models                                                                                                            | Single<br>Image<br>Reasoning | Multiple<br>Images<br>Reasoning | Image<br>Embeddings | Simple<br>Query<br>Engine |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ------------------------------- | ------------------- | ------------------------- |
| [GPT4V](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/gpt4v_multi_modal_retrieval.ipynb)<br>(OpenAI API) | ✅                           | ✅                              | 🛑                  | ✅                        |
| [CLIP](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/image_to_image_retrieval.ipynb)<br>(Local host)     | 🛑                           | 🛑                              | ✅                  | 🛑                        |
| [LLaVa](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/llava_multi_modal_tesla_10q.ipynb)<br>(replicate)  | ✅                           | 🛑                              | 🛑                  | ✅                        |
| [Fuyu-8B](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/replicate_multi_modal.ipynb)<br>(replicate)      | ✅                           | 🛑                              | 🛑                  | ✅                        |
| [ImageBind<br>](https://imagebind.metademolab.com/)[To integrate]                                                                       | 🛑                           | 🛑                              | ✅                  | 🛑                        |
| [MiniGPT-4<br>](https://minigpt-4.github.io/)[To integrate]                                                                             | ✅                           | 🛑                              | 🛑                  | ✅                        |

### Multi Modal Vector Stores

Below table lists some vector stores supporting Multi-Modal use cases. Our LlamaIndex built-in `MultiModalVectorStoreIndex` supports building separate vector stores for image and text embedding vector stores. `MultiModalRetriever`, and `SimpleMultiModalQueryEngine` support text to text/image and image to image retrieval and simple ranking fusion functions for combining text and image retrieval results.
| Multi-Modal<br>Vector Stores | Single<br>Vector<br>Store | Multiple<br>Vector<br>Stores | Text<br>Embedding | Image<br>Embedding |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | --------------------------- | --------------------------------------------------------- | ------------------------------------------------------- |
| [LLamaIndex self-built<br>MultiModal Index](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/gpt4v_multi_modal_retrieval.ipynb) | 🛑 | ✅ | Can be arbitrary<br>text embedding<br>(Default is GPT3.5) | Can be arbitrary<br>text embedding<br>(Default is CLIP) |
| [Chroma](https://github.com/run-llama/llama_index/blob/main/docs/examples/multi_modal/ChromaMultiModalDemo.ipynb) | ✅ | 🛑 | CLIP ✅ | CLIP ✅ |
| [Weaviate](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind)<br>[To integrate] | ✅ | 🛑 | CLIP ✅<br>ImageBind ✅ | CLIP ✅<br>ImageBind ✅ |

## Modules

We support integrations with GPT-4V, LLaVA, Fuyu-8B, CLIP, and more.

```{toctree}
---
maxdepth: 1
---
/examples/multi_modal/openai_multi_modal.ipynb
/examples/multi_modal/replicate_multi_modal.ipynb
/examples/multi_modal/multi_modal_retrieval.ipynb
/examples/multi_modal/llava_multi_modal_tesla_10q.ipynb
/examples/multi_modal/image_to_image_retrieval.ipynb
/examples/multi_modal/gpt4v_multi_modal_retrieval.ipynb
/examples/multi_modal/gpt4v_experiments_cot.ipynb
/examples/multi_modal/ChromaMultiModalDemo.ipynb
```

## Evaluation

We support basic evaluation for Multi-Modal LLM and RAG.

```{toctree}
---
maxdepth: 1
---
/examples/evaluation/multi_modal/multi_modal_rag_evaluation.ipynb
```
