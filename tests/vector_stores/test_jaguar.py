import json
import time

from llama_index.schema import TextNode
from llama_index.vector_stores.jaguar import JaguarVectorStore
from llama_index.vector_stores.types import (
    VectorStoreQuery,
)

#############################################################################################
##  This pytest script tests JaguarVectorStore with test cases of creating a vector store,
##  add texts to the store, similarity search in the store, search with filters, anomaly search,
##  and similarity search of records with time cutoff.
##
##  Requirement: fwww http server must be running at 127.0.0.1:8080 (or any end point)
##               jaguardb server must be running accepting commands from the http server
##
#############################################################################################


class TestJaguarVectorStore:
    vectorstore: JaguarVectorStore
    pod: str
    store: str

    @classmethod
    def setup_class(cls) -> None:
        url = "http://127.0.0.1:8080/fwww/"
        cls.pod = "vdb"
        cls.store = "llamaindex_test_store"
        vector_index = "v"
        vector_type = "cosine_fraction_float"
        vector_dimension = 3
        cls.vectorstore = JaguarVectorStore(
            cls.pod,
            cls.store,
            vector_index,
            vector_type,
            vector_dimension,
            url,
        )

    @classmethod
    def teardown_class(cls) -> None:
        pass

    def test_login(self) -> None:
        """Client must login to jaguar store server.
        Environment variable JAGUAR_API_KEY or $HOME/.jagrc file must
        contain the jaguar api key.
        """
        rc = self.vectorstore.login()
        assert rc is True

    def test_create(self) -> None:
        """Create a vector with vector index 'v' of vector_dimension.

        and 'v:text' to hold text and metadata author and category
        """
        metadata_fields = "author char(32), category char(16)"
        self.vectorstore.create(metadata_fields, 1024)

        podstore = self.pod + "." + self.store
        js = self.vectorstore.run(f"desc {podstore}")
        jd = json.loads(js[0])
        assert podstore in jd["data"]

    def test_add_texts(self) -> None:
        """Add some text nodes to the vector store.

        Here the embeddings are given. In real-life applications,
        the embeddings should be generated by an embedding model.
        """
        self.vectorstore.clear()

        node1 = TextNode(
            text="Return of King Lear",
            metadata={"author": "William", "category": "Tragedy"},
            embedding=[0.9, 0.1, 0.4],
        )

        node2 = TextNode(
            text="Slow Clouds",
            metadata={"author": "Adam", "category": "Nature"},
            embedding=[0.4, 0.2, 0.8],
        )

        node3 = TextNode(
            text="Green Machine",
            metadata={"author": "Eve", "category": "History"},
            embedding=[0.1, 0.7, 0.5],
        )

        nodes = [node1, node2, node3]

        ids = self.vectorstore.add(nodes=nodes, use_node_metadata=True)
        assert len(ids) == len(nodes)
        assert len(ids) == 3

    def test_query(self) -> None:
        """Test that [0.4, 0.2, 0.8] will retrieve text Slow Clouds.
        Here k is 1.
        """
        qembedding = [0.4, 0.2, 0.8]
        vsquery = VectorStoreQuery(query_embedding=qembedding, similarity_top_k=1)

        res = self.vectorstore.query(vsquery)

        assert res.nodes is not None
        assert res.ids is not None
        assert res.similarities is not None

        assert len(res.nodes) == 1
        assert len(res.ids) == 1
        assert len(res.similarities) == 1

        assert res.nodes[0].get_text() == "Slow Clouds"

    def test_query_filter(self) -> None:
        """Test query with filter(where condition)."""
        qembedding = [0.4, 0.2, 0.8]
        vsquery = VectorStoreQuery(query_embedding=qembedding, similarity_top_k=3)
        where = "author='Eve'"

        res = self.vectorstore.query(
            vsquery,
            where=where,
            metadata_fields=["author", "category"],
        )

        assert res.nodes is not None
        assert res.ids is not None
        assert res.similarities is not None

        assert len(res.nodes) == 1
        assert len(res.ids) == 1
        assert len(res.similarities) == 1

        assert res.nodes[0].get_text() == "Green Machine"
        assert res.nodes[0].metadata["author"] == "Eve"
        assert res.nodes[0].metadata["category"] == "History"

    def test_query_cutoff(self) -> None:
        """Test query with time cutoff."""
        qembedding = [0.4, 0.2, 0.8]
        vsquery = VectorStoreQuery(query_embedding=qembedding, similarity_top_k=3)
        args = "second_cutoff=1"

        time.sleep(2)
        res = self.vectorstore.query(
            vsquery,
            args=args,
        )

        assert res.nodes is not None
        assert res.ids is not None
        assert res.similarities is not None

        assert len(res.nodes) == 0
        assert len(res.ids) == 0
        assert len(res.similarities) == 0

    def test_search_anomalous(self) -> None:
        """Test detection of anomalousness."""
        emb = [0.7, 0.1, 0.2]
        node = TextNode(
            text="Gone With The Wind",
            embedding=emb,
        )
        result = self.vectorstore.is_anomalous(node)
        assert result is False

    def test_clear(self) -> None:
        """Test cleanup of data in the store."""
        self.vectorstore.clear()
        assert self.vectorstore.count() == 0

    def test_drop(self) -> None:
        """Destroy the vector store."""
        self.vectorstore.drop()

    def test_logout(self) -> None:
        """Client must logout to disconnect from jaguar server.

        and clean up resources used by the client
        """
        self.vectorstore.logout()
