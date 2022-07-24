from typing import Optional

from .doc_list import DocList, MemoryDocList
from .inverted_index import (
    InvertedIndex,
    MemoryInvertedIndex,
    SinglePassInMemoryInvertedIndex,
)
from .tokenize import normalized_tokens


doc_list: Optional[DocList] = None
inverted_index: Optional[InvertedIndex] = None


def init(idx_dir: str):
    global doc_list, inverted_index
    doc_list = MemoryDocList(idx_dir)
    inverted_index = SinglePassInMemoryInvertedIndex(idx_dir)


def index(name: str, text: str):
    idx = doc_list.add(name)

    # consider a text as a bag of words for now.
    tokens = normalized_tokens(text)
    inverted_index.add(idx, tokens)


def clear_index():
    doc_list.clear()
    inverted_index.clear()


def save_index():
    doc_list.save()
    inverted_index.save()


def restore_index():
    doc_list.restore()
    inverted_index.restore()


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    if len(query_tokens) == 1:
        doc_ids = inverted_index.get(query_tokens[0])
    else:
        doc_ids = inverted_index.search_and(query_tokens)
    return [doc_list.get(doc_id) for doc_id in doc_ids]


def count(query: str) -> int:
    query_tokens = normalized_tokens(query)
    return inverted_index.count_and(query_tokens)
