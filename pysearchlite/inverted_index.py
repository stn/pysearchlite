import abc
import os
import shutil
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


class SinglePassInMemoryInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str, mem_limit=1000_000_000):
        self.idx_dir = idx_dir
        os.makedirs(idx_dir, exist_ok=True)
        self.raw_data: dict[str, list[int]] = dict()
        self.data: dict[str, int] = dict()
        self.file: Optional[TextIO] = None
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_")
        self.tmp_index_num = 0
        self.raw_data_size = 0
        self.mem_limit = mem_limit

    def add(self, idx: int, tokens: set):
        POS_SIZE = 10
        TOKEN_SIZE = 20

        for token in tokens:
            if token in self.raw_data:
                self.raw_data[token].append(idx)
                self.raw_data_size += POS_SIZE
            else:
                self.raw_data[token] = [idx]
                self.raw_data_size += TOKEN_SIZE
        if self.raw_data_size > self.mem_limit:
            self.save_raw_data()

    def tmp_index_name(self, i: int):
        return os.path.join(self.tmp_dir.name, f"{i}")

    def save_raw_data(self):
        with open(self.tmp_index_name(self.tmp_index_num), 'w', encoding='utf-8') as f:
            for token in sorted(self.raw_data.keys()):
                f.write(token)
                f.write('\t')
                f.write(','.join([str(pos) for pos in self.raw_data[token]]))
                f.write('\n')
        self.raw_data = dict()
        self.raw_data_size = 0
        self.tmp_index_num += 1

    def merge_index(self, idx1, idx2):
        with open(idx1, 'r', encoding='utf-8') as f1:
            with open(idx2, 'r', encoding='utf-8') as f2:
                merged_index_name = self.tmp_index_name(self.tmp_index_num)
                self.tmp_index_num += 1
                with open(merged_index_name, 'w', encoding='utf-8') as out:
                    line1 = f1.readline()
                    line2 = f2.readline()
                    while True:
                        if not line1 or line1 == "\n":
                            while line2 and line2 != "\n":
                                out.write(line2)
                                line2 = f2.readline()
                            break
                        if not line2 or line2 == "\n":
                            while line1 and line1 != "\n":
                                out.write(line1)
                                line1 = f1.readline()
                            break
                        tp1 = line1.split('\t', maxsplit=1)
                        tp2 = line2.split('\t', maxsplit=1)
                        token1 = tp1[0]
                        token2 = tp2[0]
                        if token1 < token2:
                            out.write(line1)
                            line1 = f1.readline()
                        elif token1 > token2:
                            out.write(line2)
                            line2 = f2.readline()
                        else:
                            out.write(token1)
                            out.write('\t')
                            out.write(tp1[1][:-1])  # remove the last \n
                            out.write(',')
                            out.write(tp2[1])
                            line1 = f1.readline()
                            line2 = f2.readline()
        os.remove(idx1)
        os.remove(idx2)
        return merged_index_name

    def save(self):
        if self.raw_data_size > 0:
            self.save_raw_data()
        tmp_index_f = []
        for i in range(self.tmp_index_num):
            tmp_index_f.append(self.tmp_index_name(i))
        while len(tmp_index_f) > 1:
            merged_index_f = []
            for i in range(0, len(tmp_index_f), 2):
                xs = tmp_index_f[i:i+2]
                if len(xs) == 2:
                    merged_index_f.append(self.merge_index(*xs))
                else:
                    merged_index_f.extend(xs)
            tmp_index_f = merged_index_f
        # Copy the merged file into index
        shutil.copyfile(tmp_index_f[0], os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME))
        os.remove(tmp_index_f[0])

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

    def get(self, token: str) -> set[int]:
        pos = self.data.get(token, -1)
        if pos < 0:
            return set()
        self.file.seek(pos)
        return set(map(int, self.file.readline().split(',')))

    def clear(self):
        self.raw_data = dict()
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
