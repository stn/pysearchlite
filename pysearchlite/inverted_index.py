import abc
import math
import mmap
import os
import shutil
import sys
import tempfile
from operator import itemgetter
from typing import Optional, TextIO, BinaryIO, Union, Literal

INVERTED_INDEX_FILENAME = "inverted_index"

TOKEN_LEN_BYTES = 2
DOCID_BYTES = 4
DOCID_LEN_BYTES = 4

BYTEORDER: Literal["big", "little"] = "big"
B_INT32_0 = b"\x00\x00\x00\x00"


class InvertedIndex(abc.ABC):

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


class MemoryInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir
        os.makedirs(idx_dir, exist_ok=True)
        self.data: dict[str, list[int]] = dict()

    def add(self, idx: int, tokens: list[str]):
        for token in set(tokens):
            if token in self.data:
                self.data[token].append(idx)
            else:
                self.data[token] = [idx]

    def get(self, token: str) -> list[int]:
        ids = self.data.get(token, [])
        return ids

    def search_and(self, tokens: list[str]) -> list[int]:
        raise NotImplementedError()

    def count_and(self, tokens: list[str]) -> int:
        raise NotImplementedError()

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
        self.mmap: Optional[mmap.mmap] = None
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="pysearchlite_")
        self.tmp_index_num = 0
        self.raw_data_size = 0
        self.mem_limit = mem_limit

    def __del__(self):
        if self.mmap:
            self.mmap.close()
        if self.file:
            self.file.close()

    def add(self, idx: int, tokens: list[str]):
        POS_SIZE = 10
        TOKEN_SIZE = 20

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

    def write_token(self, f: BinaryIO, token: str):
        encoded_token = token.encode('utf-8')
        # TODO: check overflow
        f.write(len(encoded_token).to_bytes(TOKEN_LEN_BYTES, BYTEORDER))
        f.write(encoded_token)

    def read_token(self, f: Union[BinaryIO, mmap.mmap]) -> str:
        token_bytes = f.read(TOKEN_LEN_BYTES)
        if not token_bytes:
            return ""
        token_len = int.from_bytes(token_bytes, BYTEORDER)
        return f.read(token_len).decode('utf-8')

    def write_doc_ids(self, f: BinaryIO, doc_ids: list[int]):
        f.write(len(doc_ids).to_bytes(DOCID_LEN_BYTES, BYTEORDER))
        for doc_id in doc_ids:
            f.write(doc_id.to_bytes(DOCID_BYTES, BYTEORDER))

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
        self.mmap = mmap.mmap(self.file.fileno(), length=0, access=mmap.ACCESS_READ)
        token = self.read_token(self.mmap)
        while token:
            pos = self.mmap.tell()
            self.data[token] = pos
            ids_len = int.from_bytes(self.mmap.read(DOCID_LEN_BYTES), BYTEORDER)
            self.mmap.seek(ids_len * DOCID_BYTES, 1)
            token = self.read_token(self.mmap)

    def get(self, token: str) -> list[int]:
        pos = self.data.get(token, -1)
        if pos < 0:
            return []
        ids_len = int.from_bytes(self.mmap[pos:pos+DOCID_LEN_BYTES], BYTEORDER)
        pos += DOCID_LEN_BYTES
        ids = []
        for _ in range(ids_len):
            ids.append(int.from_bytes(self.mmap[pos:pos+DOCID_BYTES], BYTEORDER))
            pos += DOCID_BYTES
        return ids

    def next_doc_id(self, pos: int) -> (bytes, int):
        npos = pos + DOCID_BYTES
        doc_id = self.mmap[pos:npos]
        return doc_id, npos

    def prepare_state(self, tokens: list[str]) -> list[(int, int, int)]:
        # confirm if all tokens are in index.
        file_pos = []
        for t in tokens:
            pos = self.data.get(t, -1)
            if pos < 0:
                return []
            file_pos.append(pos)
        # state: a list of (n, file position, left)
        state = []
        for pos in file_pos:
            npos = pos + DOCID_LEN_BYTES
            doc_ids_len = int.from_bytes(self.mmap[pos:npos], BYTEORDER)
            state.append((doc_ids_len, npos, 0))  # TODO: we can remove the last 0
        state.sort(key=itemgetter(0))
        return state

    def binary_search(self, left: int, right: int, pos: int, doc_id: bytes) -> int:
        while left < right:
            m = (left + right) // 2
            m_pos = pos + m * DOCID_BYTES
            if self.mmap[m_pos:m_pos + DOCID_BYTES] < doc_id:
                left = m + 1
            else:
                right = m
        return left

    def increment_doc_id(self, b: bytes) -> bytes:
        return (int.from_bytes(b, BYTEORDER) + 1).to_bytes(DOCID_BYTES, BYTEORDER)

    def intersect_by_double_binary_search(self,
                                          a: list[bytes], left_a: int, right_a: int,
                                          pos_b: int, left_b: int, right_b: int,
                                          result: list[bytes]):
        if left_a >= right_a or left_b >= right_b:
            return

        if right_a - left_a == 1:
            ma_val = a[left_a]
            if right_b - left_b == 1:
                mb_pos = pos_b + left_b * DOCID_BYTES
                mb_val = self.mmap[mb_pos:mb_pos + DOCID_BYTES]
                if mb_val == ma_val:
                    result.append(ma_val)
                return

            mb = self.binary_search(left_b, right_b, pos_b, self.increment_doc_id(ma_val)) - 1
            if mb < left_b:
                return
            mb_pos = pos_b + mb * DOCID_BYTES
            mb_val = self.mmap[mb_pos:mb_pos + DOCID_BYTES]
            if mb_val == ma_val:
                result.append(ma_val)
            return

        ma = (left_a + right_a) // 2
        ma_val = a[ma]
        mb = self.binary_search(left_b, right_b, pos_b, self.increment_doc_id(ma_val)) - 1
        if mb < left_b:
            self.intersect_by_double_binary_search(a, ma + 1, right_a, pos_b, left_b, right_b, result)
            return

        mb_pos = pos_b + mb * DOCID_BYTES
        mb_val = self.mmap[mb_pos:mb_pos+DOCID_BYTES]
        if mb_val < ma_val:
            mb1 = mb + 1
            self.intersect_by_double_binary_search(a, left_a, ma, pos_b, left_b, mb1, result)
            self.intersect_by_double_binary_search(a, ma + 1, right_a, pos_b, mb1, right_b, result)
        else:  # mb_val == ma_val
            self.intersect_by_double_binary_search(a, left_a, ma, pos_b, left_b, mb, result)
            result.append(ma_val)
            self.intersect_by_double_binary_search(a, ma + 1, right_a, pos_b, mb + 1, right_b, result)

    def search_and(self, tokens: list[str]) -> list[int]:
        if len(tokens) == 1:
            return self.get(tokens[0])

        state = self.prepare_state(tokens)
        if not state:
            return []

        # set the initial doc ids from the first doc id list.
        doc_ids = []
        n, pos, _ = state[0]
        for _ in range(n):
            doc_ids.append(self.mmap[pos:pos+DOCID_BYTES])
            pos += DOCID_BYTES
        # find common doc ids
        for i in range(1, len(state)):
            n, pos, left = state[i]
            right = n - 1
            result = []
            from_left = True
            left_i = 0
            right_i = len(doc_ids) - 1
            while left_i <= right_i:
                if from_left:
                    doc_id = doc_ids[left_i]
                    left = self.binary_search(left, right, pos, doc_id)
                    l_pos = pos + left * DOCID_BYTES
                    if self.mmap[l_pos:l_pos+DOCID_BYTES] == doc_id:
                        result.append(doc_id)
                    left_i += 1
                    from_left = False
                else:
                    doc_id = doc_ids[right_i]
                    right = self.binary_search(left, right, pos, doc_id)
                    r_pos = pos + right * DOCID_BYTES
                    if self.mmap[r_pos:r_pos+DOCID_BYTES] == doc_id:
                        result.append(doc_id)
                    right_i -= 1
                    from_left = True
            doc_ids = result
        return [int.from_bytes(doc_id, BYTEORDER) for doc_id in doc_ids]

    def count_and(self, tokens: list[str]) -> int:
        if len(tokens) == 1:
            pos = self.data.get(tokens[0], -1)
            if pos < 0:
                return 0
            ids_len = int.from_bytes(self.mmap[pos:pos + DOCID_LEN_BYTES], BYTEORDER)
            return ids_len

        state = self.prepare_state(tokens)
        if not state:
            return 0

        # set the initial doc ids from the first doc id list.
        doc_ids = []
        n, pos, _ = state[0]
        for _ in range(n):
            doc_ids.append(self.mmap[pos:pos+DOCID_BYTES])
            pos += DOCID_BYTES
        # find common doc ids
        for i, (n_b, pos_b, _) in enumerate(state[1:]):
            result = []
            self.intersect_by_double_binary_search(doc_ids, 0, len(doc_ids), pos_b, 0, n_b, result)
            doc_ids = result
        return len(doc_ids)

    def clear(self):
        self.raw_data = dict()
        self.data = dict()
