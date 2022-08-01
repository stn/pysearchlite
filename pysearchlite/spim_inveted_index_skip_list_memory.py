import os
import random
import shutil
from array import array
from operator import itemgetter
from typing import Optional, TextIO, BinaryIO, Union, Literal

from .inverted_index import InvertedIndex

TOKEN_LEN_BYTES = 2
DOCID_BYTES = 4
DOCID_LEN_BYTES = 4

BYTEORDER: Literal["big", "little"] = "big"
B_INT32_0 = b"\x00\x00\x00\x00"

POS_SIZE = 10
TOKEN_SIZE = 20

SKIP_LIST_P = 2


def write_token(f: BinaryIO, token: str):
    encoded_token = token.encode('utf-8')
    # TODO: check overflow
    f.write(len(encoded_token).to_bytes(TOKEN_LEN_BYTES, BYTEORDER))
    f.write(encoded_token)


def read_token(f: BinaryIO) -> str:
    token_bytes = f.read(TOKEN_LEN_BYTES)
    if not token_bytes:
        return ""
    token_len = int.from_bytes(token_bytes, BYTEORDER)
    return f.read(token_len).decode('utf-8')


def write_doc_ids(f: BinaryIO, doc_ids: list[int]):
    f.write(len(doc_ids).to_bytes(DOCID_LEN_BYTES, BYTEORDER))
    for doc_id in doc_ids:
        f.write(doc_id.to_bytes(DOCID_BYTES, BYTEORDER))


def make_skip_list(ids: list[int]) -> list[array]:
    last_pointer = []
    skip_list = [array('i', [ids[0]])]
    for i in range(1, len(ids)):
        node = [ids[i]]
        level = 0
        while random.random() < (1.0 / SKIP_LIST_P):
            node.append(-1)
            if len(last_pointer) > level:
                skip_list[last_pointer[level]][level + 1] = i
                last_pointer[level] = i
            else:
                skip_list[0].append(i)
                last_pointer.append(i)
                break
            level += 1
        skip_list.append(array('i', node))
    return skip_list


def skip_list_search(b: list[array], doc_id_a: int, pos_b: int):
    doc_id_b = -1
    if len(b[0]) == 1:
        # no skip list
        for i in range(pos_b, len(b)):
            doc_id_b = b[i][0]
            if doc_id_b >= doc_id_a:
                return doc_id_b, i
        return doc_id_b, len(b)

    pos_b = [pos_b] * len(b[0])
    level = len(pos_b) - 1
    while level > 0:
        pos = pos_b[level]
        next_pos = b[pos][level]
        if next_pos >= 0 and b[next_pos][0] < doc_id_a:
            pos_b[level] = next_pos
        else:
            level -= 1
            pos_b[level] = pos
    for i in range(pos, len(b)):
        doc_id_b = b[i][0]
        if doc_id_b >= doc_id_a:
            return doc_id_b, pos_b[-1]
    return doc_id_b, pos_b[-1]


def skip_list_and(a: list[array], b: list[array]) -> array:
    result = array('i')
    pos_b = 0
    for node in a:
        doc_id_a = node[0]
        doc_id_b, pos_b = skip_list_search(b, doc_id_a, pos_b)
        if doc_id_b == doc_id_a:
            result.append(doc_id_a)
    return result


def doc_ids_and_skip_list(a: array, b: list[array]) -> array:
    result = array('i')
    pos_b = 0
    for doc_id_a in a:
        doc_id_b, pos_b = skip_list_search(b, doc_id_a, pos_b)
        if doc_id_b == doc_id_a:
            result.append(doc_id_a)
    return result


class SinglePassInMemoryInvertedIndexSkipListMemory(InvertedIndex):

    def __init__(self, idx_dir: str, mem_limit=1000_000_000):
        super().__init__(idx_dir)
        self.raw_data: dict[str, list[int]] = {}
        self.data: dict[str, list[array]] = {}
        self.file: Optional[TextIO] = None
        self.tmp_index_num = 0
        self.raw_data_size = 0
        self.mem_limit = mem_limit

    def __del__(self):
        if self.file:
            self.file.close()

    def add(self, idx: int, tokens: list[str]):
        for token in set(tokens):
            if token in self.raw_data:
                self.raw_data[token].append(idx)
                self.raw_data_size += POS_SIZE
            else:
                self.raw_data[token] = [idx]
                self.raw_data_size += TOKEN_SIZE
        if self.raw_data_size > self.mem_limit:
            self.save_raw_data()

    def tmp_index_name(self, i: int) -> str:
        return os.path.join(self.tmp_dir.name, f"{i}")

    def save_raw_data(self):
        # [len(token)] [token] [len(ids)] [ids]
        with open(self.tmp_index_name(self.tmp_index_num), 'wb') as f:
            for token in sorted(self.raw_data.keys()):  # TODO this consumes a lot of memory
                write_token(f, token)
                doc_ids = self.raw_data[token]
                write_doc_ids(f, doc_ids)
        self.raw_data = {}
        self.raw_data_size = 0
        self.tmp_index_num += 1

    def merge_index(self, idx1: str, idx2: str):
        def copy_ids(dst: BinaryIO, src: BinaryIO):
            docid_bytes = src.read(DOCID_LEN_BYTES)
            doc_ids_len = int.from_bytes(docid_bytes, BYTEORDER)
            dst.write(docid_bytes)
            doc_ids_bytes = src.read(doc_ids_len * DOCID_BYTES)
            dst.write(doc_ids_bytes)

        def merge_ids(dst: BinaryIO, src1: BinaryIO, src2: BinaryIO):
            doc_ids_len1 = int.from_bytes(src1.read(DOCID_LEN_BYTES), BYTEORDER)
            doc_ids_len2 = int.from_bytes(src2.read(DOCID_LEN_BYTES), BYTEORDER)
            dst.write((doc_ids_len1 + doc_ids_len2).to_bytes(DOCID_LEN_BYTES, BYTEORDER))
            doc_ids_bytes = src1.read(doc_ids_len1 * DOCID_BYTES)
            dst.write(doc_ids_bytes)
            doc_ids_bytes = src2.read(doc_ids_len2 * DOCID_BYTES)
            dst.write(doc_ids_bytes)

        with open(idx1, 'rb') as f1:
            with open(idx2, 'rb') as f2:
                merged_index_name = self.tmp_index_name(self.tmp_index_num)
                self.tmp_index_num += 1
                with open(merged_index_name, 'wb') as out:
                    token1 = read_token(f1)
                    token2 = read_token(f2)
                    while True:
                        if not token1:
                            while token2:
                                write_token(out, token2)
                                copy_ids(out, f2)
                                token2 = read_token(f2)
                            break
                        if not token2:
                            while token1:
                                write_token(out, token1)
                                copy_ids(out, f1)
                                token1 = read_token(f1)
                            break
                        if token1 < token2:
                            write_token(out, token1)
                            copy_ids(out, f1)
                            token1 = read_token(f1)
                        elif token1 > token2:
                            write_token(out, token2)
                            copy_ids(out, f2)
                            token2 = read_token(f2)
                        else:
                            write_token(out, token1)
                            merge_ids(out, f1, f2)
                            token1 = read_token(f1)
                            token2 = read_token(f2)
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
                xs = tmp_index_f[i:i + 2]
                if len(xs) == 2:
                    merged_index_f.append(self.merge_index(*xs))
                else:
                    merged_index_f.extend(xs)
            tmp_index_f = merged_index_f
        # Copy the merged file into index
        shutil.copyfile(tmp_index_f[0], self.get_inverted_index_filename())
        os.remove(tmp_index_f[0])

    def restore(self):
        self.data = {}
        self.file = open(self.get_inverted_index_filename(), 'rb')
        token = read_token(self.file)
        while token:
            ids_len = int.from_bytes(self.file.read(DOCID_LEN_BYTES), BYTEORDER)
            ids = []
            for i in range(ids_len):
                ids.append(int.from_bytes(self.file.read(DOCID_BYTES), BYTEORDER))
            skip_list = make_skip_list(ids)
            self.data[token] = (ids_len, skip_list)
            token = read_token(self.file)

    def get(self, token: str) -> list[int]:
        n, skip_list = self.data.get(token, (0, []))
        if n == 0:
            return []
        return [node[0] for node in skip_list]

    def prepare_state(self, tokens: list[str]) -> list[(int, list[array])]:
        state = []
        for t in tokens:
            n, ids = self.data.get(t, (0, []))
            if n == 0:
                return []
            state.append((n, ids))
        state.sort(key=itemgetter(0))
        return state

    def search_and(self, tokens: list[str]) -> list[int]:
        if len(tokens) == 1:
            return self.get(tokens[0])

        state = self.prepare_state(tokens)
        if not state:
            return []

        _, skip_list_a = state[0]
        _, skip_list_b = state[1]
        doc_ids_a = skip_list_and(skip_list_a, skip_list_b)
        # find common doc ids
        for i, (n_b, skip_list_b) in enumerate(state[2:]):
            doc_ids_a = doc_ids_and_skip_list(doc_ids_a, skip_list_b)
        return doc_ids_a.tolist()

    def count_and(self, tokens: list[str]) -> int:
        if len(tokens) == 1:
            n, _ = self.data.get(tokens[0], (0, []))
            return n

        state = self.prepare_state(tokens)
        if not state:
            return 0

        _, skip_list_a = state[0]
        _, skip_list_b = state[1]
        doc_ids_a = skip_list_and(skip_list_a, skip_list_b)
        # find common doc ids
        for _, skip_list_b in state[2:]:
            doc_ids_a = doc_ids_and_skip_list(doc_ids_a, skip_list_b)
        return len(doc_ids_a)

    def clear(self):
        self.raw_data = {}
        self.data = {}