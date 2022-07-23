import abc
import os
import shutil
import subprocess
import tempfile
from sys import byteorder
from typing import Optional, TextIO, BinaryIO

INVERTED_INDEX_FILENAME = "inverted_index"

TOKEN_LEN_BYTES = 2
DOCID_BYTES = 4
DOCID_LEN_BYTES = 4


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

    def write_token(self, f: BinaryIO, token: str):
        encoded_token = token.encode('utf-8')
        f.write(len(encoded_token).to_bytes(TOKEN_LEN_BYTES, byteorder))
        f.write(encoded_token)

    def read_token(self, f: BinaryIO) -> str:
        token_bytes = f.read(TOKEN_LEN_BYTES)
        if not token_bytes:
            return ""
        token_len = int.from_bytes(token_bytes, byteorder)
        return f.read(token_len).decode('utf-8')

    def write_doc_ids(self, f: BinaryIO, doc_ids: list[int]):
        f.write(len(doc_ids).to_bytes(DOCID_LEN_BYTES, byteorder))
        for doc_id in doc_ids:
            f.write(doc_id.to_bytes(DOCID_BYTES, byteorder))

    def save_raw_data(self):
        # [len(token)] [token] [len(ids)] [ids]
        with open(self.tmp_index_name(self.tmp_index_num), 'wb') as f:
            for token in sorted(self.raw_data.keys()):  # TODO this consumes a lot of memory
                self.write_token(f, token)
                doc_ids = self.raw_data[token]
                self.write_doc_ids(f, doc_ids)
        self.raw_data = dict()
        self.raw_data_size = 0
        self.tmp_index_num += 1

    def merge_index(self, idx1: str, idx2: str):
        def copy_ids(dst: BinaryIO, src: BinaryIO):
            docid_bytes = src.read(DOCID_LEN_BYTES)
            doc_ids_len = int.from_bytes(docid_bytes, byteorder)
            dst.write(docid_bytes)
            doc_ids_bytes = src.read(doc_ids_len * DOCID_BYTES)
            dst.write(doc_ids_bytes)

        def merge_ids(dst: BinaryIO, src1: BinaryIO, src2: BinaryIO):
            doc_ids_len1 = int.from_bytes(src1.read(DOCID_LEN_BYTES), byteorder)
            doc_ids_len2 = int.from_bytes(src2.read(DOCID_LEN_BYTES), byteorder)
            dst.write((doc_ids_len1 + doc_ids_len2).to_bytes(DOCID_LEN_BYTES, byteorder))
            doc_ids_bytes = src1.read(doc_ids_len1 * DOCID_BYTES)
            dst.write(doc_ids_bytes)
            doc_ids_bytes = src2.read(doc_ids_len2 * DOCID_BYTES)
            dst.write(doc_ids_bytes)

        with open(idx1, 'rb') as f1:
            with open(idx2, 'rb') as f2:
                merged_index_name = self.tmp_index_name(self.tmp_index_num)
                self.tmp_index_num += 1
                with open(merged_index_name, 'wb') as out:
                    token1 = self.read_token(f1)
                    token2 = self.read_token(f2)
                    while True:
                        if not token1:
                            while token2:
                                self.write_token(out, token2)
                                copy_ids(out, f2)
                                token2 = self.read_token(f2)
                            break
                        if not token2:
                            while token1:
                                self.write_token(out, token1)
                                copy_ids(out, f1)
                                token1 = self.read_token(f1)
                            break
                        if token1 < token2:
                            self.write_token(out, token1)
                            copy_ids(out, f1)
                            token1 = self.read_token(f1)
                        elif token1 > token2:
                            self.write_token(out, token2)
                            copy_ids(out, f2)
                            token2 = self.read_token(f2)
                        else:
                            self.write_token(out, token1)
                            merge_ids(out, f1, f2)
                            token1 = self.read_token(f1)
                            token2 = self.read_token(f2)
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
        self.file = open(os.path.join(self.idx_dir, INVERTED_INDEX_FILENAME), 'rb')
        token = self.read_token(self.file)
        while token:
            pos = self.file.tell()
            self.data[token] = pos
            ids_len = int.from_bytes(self.file.read(DOCID_LEN_BYTES), byteorder)
            self.file.seek(ids_len * DOCID_BYTES, 1)
            token = self.read_token(self.file)

    def get(self, token: str) -> set[int]:
        pos = self.data.get(token, -1)
        if pos < 0:
            return set()
        self.file.seek(pos)
        ids_len = int.from_bytes(self.file.read(DOCID_LEN_BYTES), byteorder)
        ids = [int.from_bytes(self.file.read(DOCID_BYTES), byteorder) for _ in range(ids_len)]
        return set(ids)

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
