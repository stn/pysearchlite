from .doc_list import DocList
from .inverted_index import InvertedIndex
from .tokenize import normalized_tokens


_doc_list = DocList()
_inverted_index = InvertedIndex()


def index(name: str, text: str):
    idx = _doc_list.add(name)

    # consider a text as a bag of words for now.
    tokens = set(normalized_tokens(text))
    _inverted_index.update(idx, tokens)


def clear_index():
    _doc_list.clear()
    _inverted_index.clear()


def save_index(idx_dir: str):
    _doc_list.save(idx_dir)
    _inverted_index.save(idx_dir)


def restore_index(idx_dir: str):
    _doc_list.restore(idx_dir)
    _inverted_index.restore(idx_dir)


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    result = None
    for token in query_tokens:
        ids = _inverted_index.get(token)
        if result is None:
            result = ids
        else:
            result &= ids
    return list(map(lambda x: _doc_list.get(x), result))
