from typing import Optional

from .doc_list import DocList, MemoryDocList
from .inverted_index import InvertedIndex
from .memory_inverted_index import MemoryInvertedIndex
from .spim_inveted_index import SinglePassInMemoryInvertedIndex
from .tokenize import normalized_tokens


DOC_LIST: Optional[DocList] = None
INVERTED_INDEX: Optional[InvertedIndex] = None


def init(idx_dir: str):
    global DOC_LIST, INVERTED_INDEX
    DOC_LIST = MemoryDocList(idx_dir)
    INVERTED_INDEX = SinglePassInMemoryInvertedIndex(idx_dir)


def index(name: str, text: str):
    idx = DOC_LIST.add(name)

    # consider a text as a bag of words for now.
    tokens = normalized_tokens(text)
    INVERTED_INDEX.add(idx, tokens)


def clear_index():
    DOC_LIST.clear()
    INVERTED_INDEX.clear()


def save_index():
    DOC_LIST.save()
    INVERTED_INDEX.save()


def restore_index():
    DOC_LIST.restore()
    INVERTED_INDEX.restore()


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    if len(query_tokens) == 1:
        doc_ids = INVERTED_INDEX.get(query_tokens[0])
    else:
        doc_ids = INVERTED_INDEX.search_and(query_tokens)
    return [DOC_LIST.get(doc_id) for doc_id in doc_ids]


def count(query: str) -> int:
    query_tokens = normalized_tokens(query)
    return INVERTED_INDEX.count_and(query_tokens)
