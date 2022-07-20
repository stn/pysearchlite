import abc
import os
from typing import Optional, TextIO


INVERTED_INDEX_FILENAME = "inverted_index"


class InvertedIndex(abc.ABC):

    @abc.abstractmethod
    def add(self, idx: int, tokens: set):
        pass

    @abc.abstractmethod
    def get(self, token: str) -> set[int]:
        pass

    @abc.abstractmethod
    def save(self, idx_dir: str):
        pass

    @abc.abstractmethod
    def restore(self, idx_dir: str):
        pass

    @abc.abstractmethod
    def clear(self):
        pass


class MemoryInvertedIndex(InvertedIndex):

    def __init__(self):
        self._data: dict[str, list[int]] = dict()

    def add(self, idx: int, tokens: set):
        for token in tokens:
            if token in self._data:
                self._data[token].append(idx)
            else:
                self._data[token] = [idx]

    def get(self, token: str) -> set[int]:
        ids = self._data.get(token, [])
        return set(ids)

    def save(self, idx_dir: str):
        with open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
            for token, pos in self._data.items():
                f.write(token)
                f.write('\t')
                f.write(','.join(map(str, pos)))
                f.write('\n')

    def restore(self, idx_dir: str):
        self._data = dict()
        with open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8') as f:
            for line in f:
                key_value = line[:-1].split('\t', maxsplit=1)
                key = key_value[0]
                pos = list(map(int, key_value[1].split(',')))
                self._data[key] = pos

    def clear(self):
        self._data = dict()
        self._data = dict()


class AsciiFileInvertedIndex(InvertedIndex):

    def __init__(self):
        self._raw_data: dict[str, list[int]] = dict()
        self._data: dict[str, int] = dict()
        self._file: Optional[TextIO] = None

    def add(self, idx: int, tokens: set):
        for token in tokens:
            if token in self._raw_data:
                self._raw_data[token].append(idx)
            else:
                self._raw_data[token] = [idx]

    def get(self, token: str) -> set[int]:
        pos = self._data.get(token, -1)
        if pos < 0:
            return set()
        self._file.seek(pos)
        return set(map(int, self._file.readline().split(',')))

    def save(self, idx_dir: str):
        with open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
            for token, pos in self._raw_data.items():
                f.write(token)
                f.write('\t')
                f.write(','.join(map(str, pos)))
                f.write('\n')

    def restore(self, idx_dir: str):
        self._data = dict()
        self._file = open(os.path.join(idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8')
        pos = 0
        line = self._file.readline()
        while line:
            key_value = line[:-1].split('\t', maxsplit=1)
            key = key_value[0]
            self._data[key] = pos + len(key.encode('utf-8')) + 1
            pos = self._file.tell()
            line = self._file.readline()

    def clear(self):
        self._raw_data = dict()
        self._data = dict()
