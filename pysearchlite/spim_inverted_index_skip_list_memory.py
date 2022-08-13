import os
import shutil
from array import array
from operator import itemgetter

from .block_skip_list import BlockSkipList
from .codecs import (
    write_token, write_doc_ids, read_token,
    copy_ids, merge_ids,
    DOCID_LEN_BYTES, BYTEORDER, DOCID_BYTES,
)
from .inverted_index import InvertedIndex


POS_SIZE = 10
TOKEN_SIZE = 20


class SinglePassInMemoryInvertedIndexSkipListMemory(InvertedIndex):

    def __init__(self, idx_dir: str, mem_limit=1000_000_000):
        super().__init__(idx_dir)
        self.raw_data: dict[str, list[int]] = {}
        self.data: dict[str, BlockSkipList] = {}
        self.tmp_index_num = 0
        self.raw_data_size = 0
        self.mem_limit = mem_limit

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
        with open(self.get_inverted_index_filename(), 'rb') as file:
            token = read_token(file)
            while token:
                ids_len = int.from_bytes(file.read(DOCID_LEN_BYTES), BYTEORDER)
                ids = []
                for i in range(ids_len):
                    ids.append(int.from_bytes(file.read(DOCID_BYTES), BYTEORDER))
                skip_list = BlockSkipList.from_list(ids)
                self.data[token] = (ids_len, skip_list)
                token = read_token(file)

    def get(self, token: str) -> list[int]:
        n, skip_list = self.data.get(token, (0, []))
        if n == 0:
            return []
        return skip_list.get_ids()

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
        doc_ids_a = skip_list_a.intersection(skip_list_b)
        # find common doc ids
        for i, (n_b, skip_list_b) in enumerate(state[2:]):
            doc_ids_a = skip_list_b.intersection_with_doc_ids(doc_ids_a)
        return doc_ids_a

    def count_and(self, tokens: list[str]) -> int:
        if len(tokens) == 1:
            n, _ = self.data.get(tokens[0], (0, []))
            return n

        state = self.prepare_state(tokens)
        if not state:
            return 0

        _, skip_list_a = state[0]
        _, skip_list_b = state[1]
        doc_ids_a = skip_list_a.intersection(skip_list_b)
        # find common doc ids
        for _, skip_list_b in state[2:]:
            doc_ids_a = skip_list_b.intersection_with_doc_ids(doc_ids_a)
        return len(doc_ids_a)

    def clear(self):
        self.raw_data = {}
        self.data = {}
