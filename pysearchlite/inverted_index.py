import abc
import os
import tempfile

INVERTED_INDEX_FILENAME = "inverted_index"


class InvertedIndex(abc.ABC):

    def __init__(self, idx_dir: str = None):
        self.idx_dir = idx_dir
        if idx_dir:
            os.makedirs(idx_dir, exist_ok=True)
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_")

    @abc.abstractmethod
    def add(self, idx: int, tokens: list[str]):
        pass

    @abc.abstractmethod
    def get(self, token: str) -> list[int]:
        pass

    @abc.abstractmethod
    def search_and(self, tokens: list[str]) -> list[int]:
        pass

    @abc.abstractmethod
    def count_and(self, tokens: list[str]) -> int:
        pass

    @abc.abstractmethod
    def save(self):
        pass

    @abc.abstractmethod
    def restore(self):
        pass

    @abc.abstractmethod
    def clear(self):
        pass

    def get_inverted_index_filename(self):
        return os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME)
