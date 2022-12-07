"""File for core data structures."""

import random
import sys
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from dataclasses_json import DataClassJsonMixin

from gpt_index.schema import BaseDocument


@dataclass
class IndexStruct(BaseDocument, DataClassJsonMixin):
    """A base data struct for a GPT index."""

    # NOTE: the text represents a summary of the content of the index struct.
    # primarily used for composing indices with other indices
    _text: Optional[str] = None
    _doc_id: Optional[str] = None

    @property
    def text(self) -> str:
        """Get text."""
        if self._text is None:
            raise ValueError("_text field not set.")
        return self._text

    @text.setter
    def text(self, text: str) -> None:
        """Set text."""
        self._text = text

    @property
    def doc_id(self) -> str:
        """Get doc_id."""
        if self._doc_id is None:
            raise ValueError("doc_id not set.")
        return self._doc_id

    @text.setter
    def doc_id(self, doc_id: str) -> None:
        """Set doc_id."""
        self._doc_id = doc_id


@dataclass
class Node(IndexStruct):
    """A generic node of data.

    Used in the GPT Tree Index and List Index.

    """

    # TODO: remove
    index: int = 0
    # used for GPTTreeIndex
    child_indices: Set[int] = field(default_factory=set)

    # embeddings
    embedding: Optional[List[float]] = None

    # reference document id
    ref_doc_id: Optional[str] = None


@dataclass
class IndexGraph(IndexStruct):
    """A graph representing the tree-structured index."""

    all_nodes: Dict[int, Node] = field(default_factory=dict)
    root_nodes: Dict[int, Node] = field(default_factory=dict)

    @property
    def size(self) -> int:
        """Get the size of the graph."""
        return len(self.all_nodes)

    def get_children(self, parent_node: Optional[Node]) -> Dict[int, Node]:
        """Get nodes given indices."""
        if parent_node is None:
            return self.root_nodes
        else:
            return {i: self.all_nodes[i] for i in parent_node.child_indices}

    def insert_under_parent(self, node: Node, parent_node: Optional[Node]) -> None:
        """Insert under parent node."""
        if node.index in self.all_nodes:
            raise ValueError(
                "Cannot insert a new node with the same index as an existing node."
            )
        if parent_node is None:
            self.root_nodes[node.index] = node
        else:
            parent_node.child_indices.add(node.index)

        self.all_nodes[node.index] = node


@dataclass
class KeywordTable(IndexStruct):
    """A table of keywords mapping keywords to text chunks."""

    table: Dict[str, Set[int]] = field(default_factory=dict)
    text_chunks: Dict[int, str] = field(default_factory=dict)

    def _get_index(self) -> int:
        """Get the next index for the text chunk."""
        # randomly generate until we get a unique index
        while True:
            idx = random.randint(0, sys.maxsize)
            if idx not in self.text_chunks:
                break
        return idx

    def add_text(self, keywords: List[str], text_chunk: str) -> int:
        """Add text to table."""
        cur_idx = self._get_index()
        for keyword in keywords:
            if keyword not in self.table:
                self.table[keyword] = set()
            self.table[keyword].add(cur_idx)
        self.text_chunks[cur_idx] = text_chunk
        return cur_idx

    def get_texts(self, keyword: str) -> List[str]:
        """Get texts given keyword."""
        if keyword not in self.table:
            raise ValueError("Keyword not found in table.")
        return [self.text_chunks[idx] for idx in self.table[keyword]]

    @property
    def keywords(self) -> Set[str]:
        """Get all keywords in the table."""
        return set(self.table.keys())

    @property
    def size(self) -> int:
        """Get the size of the table."""
        return len(self.table)


@dataclass
class IndexList(IndexStruct):
    """A list of documents."""

    nodes: List[Node] = field(default_factory=list)

    def add_text(self, text_chunk: str, ref_doc_id: int) -> int:
        """Add text to table, return current position in list."""
        # don't worry about child indices for now, nodes are all in order
        cur_node = Node(text_chunk, index=len(self.nodes), ref_doc_id=ref_doc_id)
        self.nodes.append(cur_node)
        return cur_node.index


class IndexStructType(str, Enum):
    """Index struct type."""

    TREE = "tree"
    LIST = "list"
    KEYWORD_TABLE = "keyword_table"

    def get_index_struct_cls(self) -> type:
        """Get index struct class."""
        if self == IndexStructType.TREE:
            return IndexGraph
        elif self == IndexStructType.LIST:
            return IndexList
        elif self == IndexStructType.KEYWORD_TABLE:
            return KeywordTable
        else:
            raise ValueError("Invalid index struct type.")

    @classmethod
    def from_index_struct(cls, index_struct: IndexStruct) -> "IndexStructType":
        """Get index enum from index struct class."""
        if isinstance(index_struct, IndexGraph):
            return cls.TREE
        elif isinstance(index_struct, IndexList):
            return cls.LIST
        elif isinstance(index_struct, KeywordTable):
            return cls.KEYWORD_TABLE
        else:
            raise ValueError("Invalid index struct type.")
