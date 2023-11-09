# Node Parser Usage Pattern

Node parsers are a simple abstraction that take a list of documents, and chunk them into `Node` objects, such that each node is a specific chunk of the parent document. When a document is broken into nodes, all of it's attributes are inherited to the children nodes (i.e. `metadata`, text and metadata templates, etc.). You can read more about `Node` and `Document` properties [here](/core_modules/data_modules/documents_and_nodes/root.md).

## Getting Started

### Standalone Usage

Node parsers can be used on their own:

```python
from llama_index import Document
from llama_index.node_parser import SentenceSplitter

node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)

nodes = node_parser.get_nodes_from_documents(
    [Document(text="long text")], show_progress=False
)
```

### Transformation Usage

Node parsers can be included in any set of transformations.

```python
from llama_index import SimpleDirectoryReader
from llama_index.ingestion import run_transformations
from llama_index.node_parser import TokenTextSplitter

documents = SimpleDirectoryReader("./data").load_data()

transformations = [TokenTextSplitter(), ...]

nodes = run_transformations(documents, transformations)
```

### Service Context Usage

Or set inside a `ServiceContext` to be used automatically when an index is constructed using `.from_documents()`:

```python
from llama_index import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.node_parser import SentenceSplitter

documents = SimpleDirectoryReader("./data").load_data()

node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
service_context = ServiceContext.from_defaults(node_parser=node_parser)

index = VectorStoreIndex.from_documents(
    documents, service_context=service_context
)
```
