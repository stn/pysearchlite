import os
import shutil
from bisect import bisect_left
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


class SinglePassInMemoryInvertedIndexMemoryBinary(InvertedIndex):

    def __init__(self, idx_dir: str, mem_limit=1000_000_000):
        super().__init__(idx_dir)
        self.raw_data: dict[str, list[int]] = {}
        self.data: dict[str, list[bytes]] = {}
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
                ids.append(self.file.read(DOCID_BYTES))
            self.data[token] = ids
            token = read_token(self.file)

    def get(self, token: str) -> list[bytes]:
        return self.data.get(token, [])

    def get(self, token: str) -> list[int]:
        ids = self.data.get(token, [])
        if not ids:
            return []
        return [int.from_bytes(doc_id, BYTEORDER) for doc_id in ids]

    def prepare_state(self, tokens: list[str]) -> list[(int, list[bytes])]:
        state = []
        for t in tokens:
            ids = self.data.get(t, [])
            if not ids:
                return []
            state.append((len(ids), ids))
        state.sort(key=itemgetter(0))
        return state

    def binary_search(self, a: list[bytes], doc_id: bytes, left: int, right: int) -> int:
        while left < right:
            m = (left + right) // 2
            if a[m] < doc_id:
                left = m + 1
            else:
                right = m
        return left

    def double_binary_search(self,
                             a: list[bytes], left_a: int, right_a: int,
                             b: list[bytes], left_b: int, right_b: int,
                             result: list[bytes]):
        if left_a >= right_a or left_b >= right_b:
            return

        if right_a - left_a == 1:
            ma_val = a[left_a]
            if right_b - left_b == 1:
                mb_val = b[left_b]
                if mb_val == ma_val:
                    result.append(ma_val)
                return

            mb = self.binary_search(b, ma_val, left_b, right_b)
            if mb >= right_b:
                return
            mb_val = b[mb]
            if mb_val == ma_val:
                result.append(ma_val)
            return

        ma = (left_a + right_a) // 2
        ma_val = a[ma]
        mb = self.binary_search(b, ma_val, left_b, right_b)
        if mb >= right_b:
            self.double_binary_search(a, left_a, ma, b, left_b, right_b, result)
            return

        mb_val = b[mb]
        if mb_val > ma_val:
            self.double_binary_search(a, left_a, ma, b, left_b, mb, result)
            # According to the bench mark results, the follwoing branches were slower.
            #
            # if ma - left_a <= mb - left_b:
            #     self.double_binary_search(a, left_a, ma, b, left_b, mb, result)
            # else:
            #     self.double_binary_search_b(a, left_a, ma, pos_b, left_b, mb, result)
            self.double_binary_search(a, ma + 1, right_a, b, mb, right_b, result)
            # if right_a - ma - 1 <= right_b - mb:
            #     self.double_binary_search(a, ma + 1, right_a, b, mb, right_b, result)
            # else:
            #     self.double_binary_search_b(a, ma + 1, right_a, b, mb, right_b, result)
        else:  # mb_val == ma_val
            self.double_binary_search(a, left_a, ma, b, left_b, mb, result)
            # if ma - left_a <= mb - left_b:
            #     self.double_binary_search(a, left_a, ma, b, left_b, mb, result)
            # else:
            #     self.double_binary_search_b(a, left_a, ma, b, left_b, mb, result)
            result.append(ma_val)
            self.double_binary_search(a, ma + 1, right_a, b, mb + 1, right_b, result)
            # if right_a - ma <= right_b < mb:
            #     self.double_binary_search(a, ma + 1, right_a, b, mb + 1, right_b, result)
            # else:
            #     self.double_binary_search_b(a, ma + 1, right_a, b, mb + 1, right_b, result)

    def search_and(self, tokens: list[str]) -> list[int]:
        if len(tokens) == 1:
            return self.get(tokens[0])

        state = self.prepare_state(tokens)
        if not state:
            return []

        # set the initial doc ids from the first doc id list.
        n, doc_ids = state[0]

        # find common doc ids
        for i, (n_b, pos_b) in enumerate(state[1:]):
            result = []
            self.double_binary_search(doc_ids, 0, len(doc_ids), pos_b, 0, n_b, result)
            doc_ids = result
        return [int.from_bytes(doc_id, BYTEORDER) for doc_id in doc_ids]

    def count_and(self, tokens: list[str]) -> int:
        if len(tokens) == 1:
            return len(self.data.get(tokens[0], []))

        state = self.prepare_state(tokens)
        if not state:
            return 0

        # set the initial doc ids from the first doc id list.
        n, doc_ids = state[0]

        # find common doc ids
        for i, (n_b, pos_b) in enumerate(state[1:]):
            result = []
            self.double_binary_search(doc_ids, 0, len(doc_ids), pos_b, 0, n_b, result)
            doc_ids = result
        return len(doc_ids)

    def clear(self):
        self.raw_data = {}
        self.data = {}
