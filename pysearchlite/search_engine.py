import os
import re
from typing import Optional, TextIO

ASCII = re.compile("[A-Za-z0-9]+")

DOC_LIST_FILENAME = "doc_list"
INVERTED_INDEX_FILENAME = "inverted_index"

_doc_list: list[str] = list()
_inverted_index_raw: dict[str, list[int]] = dict()
_inverted_index: dict[str, int] = dict()
_inverted_index_fp: Optional[TextIO] = None


def normalized_tokens(s: str) -> list[str]:
    return list(map(lambda x: x.lower(), ASCII.findall(s)))


def _tokenize(s: str) -> list[str]:
    return s.split()


def _update_inverted_index(tokens: set, idx: int) -> None:
    for token in tokens:
        if token in _inverted_index_raw:
            _inverted_index_raw[token].append(idx)
        else:
            _inverted_index_raw[token] = [idx]


def index(name: str, text: str):
    idx = len(_doc_list)
    _doc_list.append(name)

    # consider a text as a bag of words for now.
    tokens = set(_tokenize(text))
    _update_inverted_index(tokens, idx)


def clear_index() -> None:
    global _doc_list, _inverted_index_raw, _inverted_index
    _doc_list = list()
    _inverted_index_raw = dict()
    _inverted_index = dict()


def save_doc_list(idx_dir: str) -> None:
    with open(os.path.join(idx_dir, DOC_LIST_FILENAME), 'w', encoding='utf-8') as f:
        for name in _doc_list:
            f.write(name)
            f.write('\n')


def save_inverted_index(idx_dir: str) -> None:
    with open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
        for token, pos in _inverted_index_raw.items():
            f.write(token)
            f.write('\t')
            f.write(','.join(map(str, pos)))
            f.write('\n')


def save_index(idx_dir: str) -> None:
    save_doc_list(idx_dir)
    save_inverted_index(idx_dir)


def restore_doc_list(idx_dir: str) -> None:
    global _doc_list
    _doc_list = []
    with open(os.path.join(idx_dir, DOC_LIST_FILENAME), 'r', encoding='utf-8') as f:
        for line in f:
            _doc_list.append(line[:-1])


def restore_inverted_index(idx_dir: str) -> None:
    global _inverted_index, _inverted_index_fp
    _inverted_index = dict()
    with open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8') as f:
        pos = 0
        line = f.readline()
        while line:
            key_value = line[:-1].split('\t', maxsplit=1)
            key = key_value[0]
            _inverted_index[key_value[0]] = pos + len(key.encode('utf-8')) + 1
            pos = f.tell()
            line = f.readline()
    _inverted_index_fp = open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8')


def restore_index(idx_dir: str) -> None:
    restore_doc_list(idx_dir)
    restore_inverted_index(idx_dir)


def _get_doc_ids(token: str) -> set[int]:
    pos = _inverted_index.get(token, -1)
    if pos < 0:
        return set()
    _inverted_index_fp.seek(pos)
    return set(map(int, _inverted_index_fp.readline().split(',')))


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    result = None
    for token in query_tokens:
        ids = _get_doc_ids(token)
        if result is None:
            result = ids
        else:
            result &= ids
    return list(map(lambda x: _doc_list[x], result))
