import abc
import os
import subprocess
import tempfile
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
    def save(self):
        pass

    @abc.abstractmethod
    def restore(self):
        pass

    @abc.abstractmethod
    def clear(self):
        pass


class MemoryInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir
        os.makedirs(idx_dir, exist_ok=True)
        self.data: dict[str, list[int]] = dict()

    def add(self, idx: int, tokens: set):
        for token in tokens:
            if token in self.data:
                self.data[token].append(idx)
            else:
                self.data[token] = [idx]

    def get(self, token: str) -> set[int]:
        ids = self.data.get(token, [])
        return set(ids)

    def save(self):
        with open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
            for token, pos in self.data.items():
                f.write(token)
                f.write('\t')
                f.write(','.join(map(str, pos)))
                f.write('\n')

    def restore(self):
        self.data = dict()
        with open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8') as f:
            for line in f:
                key_value = line[:-1].split('\t', maxsplit=1)
                key = key_value[0]
                pos = list(map(int, key_value[1].split(',')))
                self.data[key] = pos

    def clear(self):
        self.data = dict()


class AsciiFileInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir
        os.makedirs(idx_dir, exist_ok=True)
        self.raw_data: dict[str, list[int]] = dict()
        self.data: dict[str, int] = dict()
        self.file: Optional[TextIO] = None

    def add(self, idx: int, tokens: set):
        for token in tokens:
            if token in self.raw_data:
                self.raw_data[token].append(idx)
            else:
                self.raw_data[token] = [idx]

    def get(self, token: str) -> set[int]:
        pos = self.data.get(token, -1)
        if pos < 0:
            return set()
        self.file.seek(pos)
        return set(map(int, self.file.readline().split(',')))

    def save(self):
        with open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
            for token, pos in self.raw_data.items():
                f.write(token)
                f.write('\t')
                f.write(','.join(map(str, pos)))
                f.write('\n')

    def restore(self):
        self.data = dict()
        self.file = open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8')
        pos = 0
        line = self.file.readline()
        while line:
            key_value = line[:-1].split('\t', maxsplit=1)
            key = key_value[0]
            self.data[key] = pos + len(key.encode('utf-8')) + 1
            pos = self.file.tell()
            line = self.file.readline()

    def clear(self):
        self.raw_data = dict()
        self.data = dict()


class SortBasedInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir
        os.makedirs(idx_dir, exist_ok=True)
        self.term_doc_file: Optional[TextIO] = \
            tempfile.NamedTemporaryFile(prefix="pysearchlite-", mode="w", encoding="utf-8")
        self.data: dict[str, int] = dict()
        self.file: Optional[TextIO] = None

    def __del__(self):
        if self.term_doc_file is not None:
            self.term_doc_file.close()

    def add(self, idx: int, tokens: set):
        for token in tokens:
            self.term_doc_file.write(token)
            self.term_doc_file.write(' ')
            self.term_doc_file.write(str(idx))
            self.term_doc_file.write('\n')

    def get(self, token: str) -> set[int]:
        pos = self.data.get(token, -1)
        if pos < 0:
            return set()
        self.file.seek(pos)
        return set(map(int, self.file.readline().split(',')))

    def save(self):

        def save_term(term, doc_ids):
            f.write(term)
            f.write('\t')
            f.write(','.join(map(str, sorted(doc_ids))))
            f.write('\n')

        self.term_doc_file.flush()
        out = subprocess.run(["sort", "-k", "1", self.term_doc_file.name], encoding='utf-8', stdout=subprocess.PIPE)
        with open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'w', encoding='utf-8') as f:
            last_term = None
            doc_ids = []
            for line in out.stdout.split('\n'):
                if line == "":
                    break
                td = line.split()
                term = td[0]
                if term != last_term:
                    if last_term is not None:
                        save_term(last_term, doc_ids)
                    last_term = term
                    doc_ids = [int(td[1])]
                else:
                    doc_ids.append(int(td[1]))
            if last_term is not None:
                save_term(last_term, doc_ids)
        self.term_doc_file.close()
        self.term_doc_file = None

    def restore(self):
        self.data = dict()
        self.file = open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'r', encoding='utf-8')
        pos = 0
        line = self.file.readline()
        while line:
            key_value = line[:-1].split('\t', maxsplit=1)
            key = key_value[0]
            self.data[key] = pos + len(key.encode('utf-8')) + 1
            pos = self.file.tell()
            line = self.file.readline()

    def clear(self):
        self.data = dict()
