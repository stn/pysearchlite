from typing import Optional

from .doc_list import DocList, MemoryDocList
from .inverted_index import (
    InvertedIndex,
    AsciiFileInvertedIndex,
    MemoryInvertedIndex,
    SinglePassInMemoryInvertedIndex,
    SortBasedInvertedIndex,
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
    tokens = set(normalized_tokens(text))
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
    result = None
    for token in query_tokens:
        ids = inverted_index.get(token)
        if result is None:
            result = ids
        else:
            result &= ids
    return list(map(lambda x: doc_list.get(x), result))
