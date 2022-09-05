import mmap
import os
import shutil
import sys
from operator import itemgetter


from .block_skip_list import (
    BlockSkipList,
    BlockSkipListExt,
    DocIdListExt,
    LIST_TYPE_DOC_ID,
    LIST_TYPE_DOC_IDS_LIST,
    LIST_TYPE_SKIP_LIST,
)
from .gamma_codecs import (
    BLOCK_TYPE_DOC_ID,
    BLOCK_TYPE_DOC_IDS_LIST,
    BLOCK_TYPE_SKIP_LIST,
    DOCID_LEN_BYTES,
    SKIP_LIST_BLOCK_INDEX_BYTES,
    copy_ids,
    decode_docid,
    merge_ids,
    read_doc_ids,
    read_token,
    write_doc_ids,
    write_token,
)
from .gamma_codecs import bytes_docid
from .inverted_index import InvertedIndex


POS_SIZE = 10
TOKEN_SIZE = 20


class InvertedIndexBlockSkipList(InvertedIndex):

    def __init__(self, idx_dir, mem_limit=1000_000_000):
        super().__init__(idx_dir)
        self.raw_data = {}
        self.data = {}
        self.tmp_index_num = 0
        self.raw_data_size = 0
        self.mem_limit = mem_limit

    def add(self, idx, tokens):
        for token in set(tokens):
            if token in self.raw_data:
                self.raw_data[token].append(idx)
                self.raw_data_size += POS_SIZE
            else:
                self.raw_data[token] = [idx]
                self.raw_data_size += TOKEN_SIZE
        if self.raw_data_size > self.mem_limit:
            self.save_raw_data()

    def tmp_index_name(self, i):
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

    def merge_index(self, idx1, idx2):
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

    def convert_to_skip_list(self, idx):
        with open(idx, 'rb') as f:
            new_index_name = self.tmp_index_name(self.tmp_index_num)
            self.tmp_index_num += 1
            with open(new_index_name, 'wb') as out:
                token = read_token(f)
                while token:
                    write_token(out, token)
                    doc_ids = read_doc_ids(f)
                    skip_list = BlockSkipList.from_list(doc_ids)
                    skip_list.write(out)
                    token = read_token(f)
        os.remove(idx)
        return new_index_name

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
        # add skip list to each doc id list
        tmp_index_f = self.convert_to_skip_list(tmp_index_f[0])
        # Copy the merged file into index
        shutil.copyfile(tmp_index_f, self.get_inverted_index_filename())
        os.remove(tmp_index_f)

    def restore(self):
        self.data = {}
        with open(self.get_inverted_index_filename(), 'rb') as file:
            with mmap.mmap(file.fileno(), length=0, access=mmap.ACCESS_READ) as mem:
                token = read_token(mem)
                while token:
                    block_type = mem.read(1)
                    if block_type == BLOCK_TYPE_DOC_ID:
                        pos = mem.tell()
                        docid = mem.read(bytes_docid(mem, pos))
                        self.data[token] = (1, LIST_TYPE_DOC_ID, docid)
                    elif block_type == BLOCK_TYPE_DOC_IDS_LIST:
                        ids_len = int.from_bytes(mem.read(DOCID_LEN_BYTES), sys.byteorder)
                        pos = mem.tell()
                        end_pos = pos
                        for _ in range(ids_len):
                            end_pos += bytes_docid(mem, end_pos)
                        docids = mem.read(end_pos - pos)
                        self.data[token] = (ids_len, LIST_TYPE_DOC_IDS_LIST, docids)
                    elif block_type == BLOCK_TYPE_SKIP_LIST:
                        freq = int.from_bytes(mem.read(DOCID_LEN_BYTES), sys.byteorder)
                        pos = mem.tell()
                        block_size = int.from_bytes(mem.read(1), sys.byteorder)
                        max_level = int.from_bytes(mem.read(1), sys.byteorder)
                        mem.seek(SKIP_LIST_BLOCK_INDEX_BYTES * max_level, 1)
                        blocks = int.from_bytes(mem.read(SKIP_LIST_BLOCK_INDEX_BYTES), sys.byteorder)
                        mem.seek(blocks * block_size, 1)
                        end_pos = mem.tell()
                        mem.seek(pos)
                        skip_list_mem = mem.read(end_pos - pos)
                        self.data[token] = (freq, LIST_TYPE_SKIP_LIST, skip_list_mem)
                    else:
                        raise ValueError(f"Unsupported block type: {block_type}")
                    token = read_token(mem)

    def get(self, token):
        freq, list_type, mem = self.data.get(token, (0, 0, None))
        if freq == 0:
            return []
        elif freq == 1:
            return [decode_docid(mem, 0)]
        elif list_type == LIST_TYPE_DOC_IDS_LIST:
            list_pos = DocIdListExt(mem, freq).get_ids()
            return [decode_docid(mem, pos) for pos in list_pos]
        elif list_type == LIST_TYPE_SKIP_LIST:
            list_pos = BlockSkipListExt(mem, freq).get_ids()
            return [decode_docid(mem, pos) for pos in list_pos]

    def prepare_state(self, tokens):
        # confirm if all tokens are in index.
        state = []
        for t in tokens:
            freq, list_type, mem = self.data.get(t, (0, 0, None))
            if freq == 0:
                return []
            doc_list = BlockSkipListExt.of(freq, list_type, mem)
            state.append((freq, doc_list))
        state.sort(key=itemgetter(0))
        return state

    def search_and(self, tokens):
        if len(tokens) == 1:
            return self.get(tokens[0])

        state = self.prepare_state(tokens)
        if not state:
            return []

        result = []
        iters = [skip_list.get_iter() for _, skip_list in state]

        # find a common doc id in the first and second list.
        a_iter = iters[0]
        pos_a = a_iter.get_pos()
        b_iter = iters[1]
        while True:
            while True:
                pos_b, cmp = b_iter.search(a_iter.mem, pos_a)
                if cmp > 0:
                    pos_a, cmp_a = a_iter.search(b_iter.mem, pos_b)
                    if cmp_a == 0:
                        break
                    elif cmp_a < 0:
                        return result
                elif cmp == 0:
                    break
                else:  # reach to the end of b
                    return result

            # check the common doc id against the remains.
            for it in iters[2:]:
                pos_it, cmp = it.search(a_iter.mem, pos_a)
                if cmp > 0:
                    pos_a, cmp_a = a_iter.search(it.mem, pos_it)
                    if cmp_a < 0:
                        return result
                    break
                elif cmp < 0:  # reach to the end of the list
                    return result
            else:
                result.append(decode_docid(a_iter.mem, pos_a))
                pos_a, cmp = a_iter.next_pos()
                if cmp < 0:
                    return result

    def count_and(self, tokens):
        if len(tokens) == 1:
            # TODO self.data.get is overkill if there is a method to get freq of data.
            freq, _, _ = self.data.get(tokens[0], (0, 0, None))
            return freq

        state = self.prepare_state(tokens)
        if not state:
            return 0

        count = 0
        iters = [skip_list.get_iter() for _, skip_list in state]

        # find a common doc id in the first and second list.
        a_iter = iters[0]
        pos_a = a_iter.get_pos()
        b_iter = iters[1]
        iters2 = iters[2:]
        while True:
            while True:
                pos_b, cmp = b_iter.search(a_iter.mem, pos_a)
                if cmp > 0:
                    pos_a, cmp_a = a_iter.search(b_iter.mem, pos_b)
                    if cmp_a == 0:
                        break
                    elif cmp_a < 0:
                        return count
                elif cmp == 0:
                    break
                else:  # reach to the end of b
                    return count

            # check the common doc id against the remains.
            for it in iters2:
                pos_it, cmp = it.search(a_iter.mem, pos_a)
                if cmp > 0:
                    pos_a, cmp_a = a_iter.search(it.mem, pos_it)
                    if cmp_a < 0:
                        return count
                    break
                elif cmp < 0:  # reach to the end of the list
                    return count
            else:
                count += 1
                pos_a, cmp = a_iter.next_pos()
                if cmp < 0:
                    return count

    def clear(self):
        self.raw_data = {}
        self.data = {}
