import re


ASCII = re.compile("[A-Za-z0-9]+")

DOC_LIST: list[str] = []
INVERTED_INDEX: dict[str, list[int]] = dict()


def normalized_tokens(s: str) -> list[str]:
    return list(map(lambda x: x.lower(), ASCII.findall(s)))


def _tokenize(s: str) -> list[str]:
    return s.split()


def _update_inverted_index(tokens: set, idx: int) -> None:
    for token in tokens:
        if token in INVERTED_INDEX:
            INVERTED_INDEX[token].append(idx)
        else:
            INVERTED_INDEX[token] = [idx]


def index(name: str, text: str):
    idx = len(DOC_LIST)
    DOC_LIST.append(name)

    # consider a text as a bag of words for now.
    tokens = set(_tokenize(text))
    _update_inverted_index(tokens, idx)


def search(query: str) -> list[str]:
    query_tokens = normalized_tokens(query)
    result = None
    for token in query_tokens:
        ids = set(INVERTED_INDEX.get(token, []))
        if result is None:
            result = ids
        else:
            result &= ids
    return list(map(lambda x: DOC_LIST[x], result))
