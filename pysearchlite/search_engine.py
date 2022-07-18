import os
import re


ASCII = re.compile("[A-Za-z0-9]+")

DOC_LIST_FILENAME = "doc_list"
INVERTED_INDEX_FILENAME = "inverted_index"

_doc_list: list[str] = []
_inverted_index: dict[str, list[int]] = dict()


def normalized_tokens(s: str) -> list[str]:
    return list(map(lambda x: x.lower(), ASCII.findall(s)))


def _tokenize(s: str) -> list[str]:
    return s.split()


def _update_inverted_index(tokens: set, idx: int) -> None:
    for token in tokens:
        if token in _inverted_index:
            _inverted_index[token].append(idx)
        else:
            _inverted_index[token] = [idx]


def index(name: str, text: str):
    idx = len(_doc_list)
    _doc_list.append(name)

    # consider a text as a bag of words for now.
    tokens = set(_tokenize(text))
    _update_inverted_index(tokens, idx)


def save_index(idx_dir: str) -> None:
    os.makedirs(idx_dir, exist_ok=True)
    with open(os.path.join(idx_dir, 'doc_list'), 'w', encoding='utf-8') as f:
        for name in _doc_list:
            f.write(name)
            f.write('\n')
    with open(os.path.join(idx_dir, 'inverted_index'), 'w', encoding='utf-8') as f:
        for token, pos in _inverted_index.items():
            f.write(token)
            f.write('\t')
            f.write(','.join(map(str, pos)))
            f.write('\n')


def restore_index(idx_dir: str) -> None:
    global _doc_list, _inverted_index
    _doc_list = []
    _inverted_index = dict()
    with open(os.path.join(idx_dir, 'doc_list'), 'r', encoding='utf-8') as f:
        for line in f:
            _doc_list.append(line[:-1])
    with open(os.path.join(idx_dir, 'inverted_index'), 'r', encoding='utf-8') as f:
        for line in f:
            key_value = line[:-1].split('\t', maxsplit=1)
            pos = list(map(int, key_value[1].split(',')))
            _inverted_index[key_value[0]] = pos


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    result = None
    for token in query_tokens:
        ids = set(_inverted_index.get(token, []))
        if result is None:
            result = ids
        else:
            result &= ids
    return list(map(lambda x: _doc_list[x], result))
