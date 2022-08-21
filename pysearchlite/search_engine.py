from typing import Optional

from .codecs import BYTEORDER
from .doc_list import DocList, MemoryDocList
from .inverted_index import InvertedIndex
from .inverted_index_skip_list import InvertedIndexBlockSkipList
# from .memory_inverted_index import MemoryInvertedIndex
# from .spim_inverted_index import SinglePassInMemoryInvertedIndex
# from .spim_inverted_index_memory import SinglePassInMemoryInvertedIndexMemory
# from .spim_inverted_index_skip_list_memory import SinglePassInMemoryInvertedIndexSkipListMemory
# from .spim_inverted_index_memory_binary import SinglePassInMemoryInvertedIndexMemoryBinary
from .tokenize import normalized_tokens


DOC_LIST = None
INVERTED_INDEX = None


def init(idx_dir):
    global DOC_LIST, INVERTED_INDEX
    DOC_LIST = MemoryDocList(idx_dir)
    # INVERTED_INDEX = SinglePassInMemoryInvertedIndexMemory(idx_dir)
    # INVERTED_INDEX = SinglePassInMemoryInvertedIndexSkipListMemory(idx_dir)
    INVERTED_INDEX = InvertedIndexBlockSkipList(idx_dir)


def index(name, text):
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


def search(query):
    query_tokens = normalized_tokens(query)
    if len(query_tokens) == 1:
        doc_ids = INVERTED_INDEX.get(query_tokens[0])
    else:
        doc_ids = INVERTED_INDEX.search_and(query_tokens)
    return [DOC_LIST.get(doc_id) for doc_id in doc_ids]


def count(query):
    query_tokens = normalized_tokens(query)
    return INVERTED_INDEX.count_and(query_tokens)
