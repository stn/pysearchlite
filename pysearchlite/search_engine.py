import os
from functools import reduce
from glob import glob

from .doc_list import MemoryDocList
from .gamma_codecs import VAR_ENCODE_MAX3
from .inverted_index import INVERTED_INDEX_FILENAME
from .inverted_index_skip_list import InvertedIndexBlockSkipList
from .tokenize import normalized_tokens


INDEX_DIR = None
DOC_LIST = None
INVERTED_INDEX = []

MAX_NDOC = VAR_ENCODE_MAX3 - 1


def init(idx_dir):
    global DOC_LIST, INVERTED_INDEX, INDEX_DIR
    INDEX_DIR = idx_dir
    DOC_LIST = MemoryDocList(idx_dir)
    INVERTED_INDEX = [InvertedIndexBlockSkipList(idx_dir, 0)]


def index(name, text):
    idx = DOC_LIST.add(name)

    tokens = normalized_tokens(text)
    last_inverted_index = INVERTED_INDEX[-1]
    last_inverted_index.add(idx, tokens)
    if last_inverted_index.get_ndoc() >= MAX_NDOC:
        last_inverted_index.save_raw_data()
        INVERTED_INDEX.append(InvertedIndexBlockSkipList(INDEX_DIR, len(INVERTED_INDEX)))


def clear_index():
    DOC_LIST.clear()
    list(map(lambda x: x.clear(), INVERTED_INDEX))


def save_index():
    DOC_LIST.save()
    list(map(lambda x: x.save(), INVERTED_INDEX))


def restore_index():
    global INVERTED_INDEX
    DOC_LIST.restore()
    inverted_index_files = glob(os.path.join(INDEX_DIR, INVERTED_INDEX_FILENAME) + "_*")
    INVERTED_INDEX = [InvertedIndexBlockSkipList(INDEX_DIR, i) for i in range(len(inverted_index_files))]
    list(map(lambda x: x.restore(), INVERTED_INDEX))


def search(query):
    query_tokens = normalized_tokens(query)
    if len(query_tokens) == 1:
        doc_ids = reduce(list.__add__, map(lambda x: x.get(query_tokens[0]), INVERTED_INDEX))
    else:
        doc_ids = reduce(list.__add__, map(lambda x: x.search_and(query_tokens), INVERTED_INDEX))
    return [DOC_LIST.get(doc_id) for doc_id in doc_ids]


def count(query):
    query_tokens = normalized_tokens(query)
    return reduce(int.__add__, map(lambda x: x.count_and(query_tokens), INVERTED_INDEX))
