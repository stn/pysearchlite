import os
from functools import reduce
from glob import glob
from multiprocessing import Process, Pipe

from .doc_list import MemoryDocList
from .gamma_codecs import VAR_ENCODE_MAX3
from .inverted_index import INVERTED_INDEX_FILENAME
from .inverted_index_skip_list import InvertedIndexBlockSkipList
from .tokenize import normalized_tokens


INDEX_DIR = None
DOC_LIST = None
INVERTED_INDEX = []

MAX_NDOC = VAR_ENCODE_MAX3 - 1

PROCESSES = []
PARENT_CONN = []

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
    DOC_LIST.restore()
    inverted_index_files = glob(os.path.join(INDEX_DIR, INVERTED_INDEX_FILENAME) + "_*")
    for i in range(len(inverted_index_files)):
        parent_conn, child_conn = Pipe()
        process = Process(target=inverted_index_worker, args=(INDEX_DIR, i, child_conn,))
        process.start()
        PROCESSES.append(process)
        PARENT_CONN.append(parent_conn)


def inverted_index_worker(index_dir, sub_id, conn):
    inverted_index = InvertedIndexBlockSkipList(index_dir, sub_id)
    inverted_index.restore()
    while True:
        try:
            line = conn.recv()
            line = line.split(' ')
            command = line[0]
            args = line[1:]
            if command == 'SEARCH':
                if len(args) == 1:
                    doc_ids = inverted_index.get(args[0])
                    conn.send(doc_ids)
                else:
                    doc_ids = inverted_index.search_and(args)
                    conn.send(doc_ids)
            elif command == 'COUNT':
                c = inverted_index.count_and(args)
                conn.send(c)
        except EOFError:
            break


def search(query):
    query_tokens = normalized_tokens(query)
    command_line = 'SEARCH ' + ' '.join(query_tokens)
    for conn in PARENT_CONN:
        conn.send(command_line)
    doc_ids = reduce(list.__add__, map(lambda c: c.recv(), PARENT_CONN))
    return [DOC_LIST.get(doc_id) for doc_id in doc_ids]


def count(query):
    query_tokens = normalized_tokens(query)
    command_line = 'COUNT ' + ' '.join(query_tokens)
    for conn in PARENT_CONN:
        conn.send(command_line)
    return reduce(int.__add__, map(lambda c: c.recv(), PARENT_CONN))


def close():
    global INVERTED_INDEX, PARENT_CONN, PROCESSES
    INVERTED_INDEX = []
    PARENT_CONN = []
    for p in PROCESSES:
        p.terminate()
    PROCESSES = []
