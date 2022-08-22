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


NDOC_BYTES = 4
DOCID_OFFSET_BYTES = 4


class InvertedIndexBlockSkipList(InvertedIndex):

    def __init__(self, idx_dir, sub_id):
        super().__init__(idx_dir)
        self.sub_id = sub_id
        self.raw_data = {}
        self.data = {}
        self.file = None
        self.mmap = None
        self.tmp_index_num = 0
        self.ndoc = 0
        self.docid_offset = None

    def __del__(self):
        if self.mmap:
            self.mmap.close()
        if self.file:
            self.file.close()

    def add(self, docid, tokens):
        if self.ndoc == 0:
            self.docid_offset = docid
        self.ndoc += 1
        docid -= self.docid_offset
        # consider a text as a bag of words for now.
        for token in set(tokens):
            if token in self.raw_data:
                self.raw_data[token].append(docid)
            else:
                self.raw_data[token] = [docid]
        #if self.ndoc >= MAX_NDOC:
        #    self.save_raw_data()

    def get_inverted_index_filename(self):
        return f"{super().get_inverted_index_filename()}_{self.sub_id}"

    def tmp_index_name(self, i):
        return os.path.join(self.tmp_dir.name, f"_{self.sub_id}_{i}")

    def save_raw_data(self):
        # [len(token)] [token] [len(ids)] [ids]
        with open(self.tmp_index_name(self.tmp_index_num), 'wb') as f:
            f.write(self.ndoc.to_bytes(NDOC_BYTES, sys.byteorder))
            f.write(self.docid_offset.to_bytes(DOCID_OFFSET_BYTES, sys.byteorder))
            for token in sorted(self.raw_data.keys()):  # TODO this consumes a lot of memory
                write_token(f, token)
                doc_ids = self.raw_data[token]
                write_doc_ids(f, doc_ids)
        self.raw_data = {}
        self.ndoc = 0
        self.tmp_index_num += 1

    def merge_index(self, idx1, idx2):
        with open(idx1, 'rb') as f1:
            with open(idx2, 'rb') as f2:
                merged_index_name = self.tmp_index_name(self.tmp_index_num)
                self.tmp_index_num += 1
                with open(merged_index_name, 'wb') as out:
                    ndoc1 = int.from_bytes(f1.read(NDOC_BYTES), sys.byteorder)
                    docid_offset1 = int.from_bytes(f1.read(DOCID_OFFSET_BYTES), sys.byteorder)
                    ndoc2 = int.from_bytes(f2.read(NDOC_BYTES), sys.byteorder)
                    docid_offset2 = int.from_bytes(f2.read(DOCID_OFFSET_BYTES), sys.byteorder)
                    # TODO use docid_offset{1, 2}
                    out.write((ndoc1 + ndoc2).to_bytes(NDOC_BYTES, sys.byteorder))
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
                ndoc = int.from_bytes(f.read(NDOC_BYTES), sys.byteorder)
                docid_offset = int.from_bytes(f.read(DOCID_OFFSET_BYTES), sys.byteorder)
                out.write(docid_offset.to_bytes(DOCID_OFFSET_BYTES, sys.byteorder))
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
        if self.ndoc > 0:
            self.save_raw_data()
        tmp_index_f = []
        for i in range(self.tmp_index_num):
            tmp_index_f.append(self.tmp_index_name(i))
        # add skip list to each doc id list
        tmp_index_f = self.convert_to_skip_list(tmp_index_f[0])
        # Copy the merged file into index
        shutil.copyfile(tmp_index_f, self.get_inverted_index_filename())
        os.remove(tmp_index_f)

    def restore(self):
        self.data = {}
        self.file = open(self.get_inverted_index_filename(), 'rb')
        self.mmap = mmap.mmap(self.file.fileno(), length=0, access=mmap.ACCESS_READ)
        self.docid_offset = int.from_bytes(self.mmap.read(DOCID_OFFSET_BYTES), sys.byteorder)
        token = read_token(self.mmap)
        while token:
            block_type = self.mmap.read(1)
            if block_type == BLOCK_TYPE_DOC_ID:
                pos = self.mmap.tell()
                self.data[token] = (1, LIST_TYPE_DOC_ID, pos)
                self.mmap.seek(bytes_docid(self.mmap, pos), 1)
            elif block_type == BLOCK_TYPE_DOC_IDS_LIST:
                ids_len = int.from_bytes(self.mmap.read(DOCID_LEN_BYTES), sys.byteorder)
                pos = self.mmap.tell()
                self.data[token] = (ids_len, LIST_TYPE_DOC_IDS_LIST, pos)
                for _ in range(ids_len):
                    pos += bytes_docid(self.mmap, pos)
                self.mmap.seek(pos)
            elif block_type == BLOCK_TYPE_SKIP_LIST:
                freq = int.from_bytes(self.mmap.read(DOCID_LEN_BYTES), sys.byteorder)
                pos = self.mmap.tell()
                self.data[token] = (freq, LIST_TYPE_SKIP_LIST, pos)
                block_size = int.from_bytes(self.mmap.read(1), sys.byteorder)
                max_level = int.from_bytes(self.mmap.read(1), sys.byteorder)
                self.mmap.seek(SKIP_LIST_BLOCK_INDEX_BYTES * max_level, 1)
                blocks = int.from_bytes(self.mmap.read(SKIP_LIST_BLOCK_INDEX_BYTES), sys.byteorder)
                self.mmap.seek(blocks * block_size, 1)
            else:
                raise ValueError(f"Unsupported block type: {block_type}")
            token = read_token(self.mmap)

    def get(self, token):
        freq, list_type, pos = self.data.get(token, (0, 0, 0))
        if freq == 0:
            return []
        elif freq == 1:
            return [decode_docid(self.mmap, pos) + self.docid_offset]
        elif list_type == LIST_TYPE_DOC_IDS_LIST:
            list_pos = DocIdListExt(self.mmap, pos, freq).get_ids()
            return [decode_docid(self.mmap, pos) + self.docid_offset for pos in list_pos]
        elif list_type == LIST_TYPE_SKIP_LIST:
            list_pos = BlockSkipListExt(self.mmap, pos, freq).get_ids()
            return [decode_docid(self.mmap, pos) + self.docid_offset for pos in list_pos]
        raise ValueError

    def prepare_state(self, tokens):
        # confirm if all tokens are in index.
        state = []
        for t in tokens:
            freq, list_type, pos = self.data.get(t, (0, 0, 0))
            if freq == 0:
                return []
            state.append((freq, list_type, pos))
        state.sort(key=itemgetter(0))
        return state

    def search_and(self, tokens):
        if len(tokens) == 1:
            return self.get(tokens[0])

        state = self.prepare_state(tokens)
        if not state:
            return []

        freq_a, list_type_a, pos_a = state[0]
        freq_b, list_type_b, pos_b = state[1]
        list_a = BlockSkipListExt.of(freq_a, list_type_a, self.mmap, pos_a)
        list_b = BlockSkipListExt.of(freq_b, list_type_b, self.mmap, pos_b)
        list_pos_a = list_a.intersection(list_b)
        # find common doc ids
        for freq_b, list_type_b, pos_b in state[2:]:
            list_b = BlockSkipListExt.of(freq_b, list_type_b, self.mmap, pos_b)
            list_pos_a = list_b.intersection_with_doc_ids(self.mmap, list_pos_a)
        return [decode_docid(self.mmap, pos) + self.docid_offset for pos in list_pos_a]

    def count_and(self, tokens):
        if len(tokens) == 1:
            freq, _, _ = self.data.get(tokens[0], (0, 0, 0))
            return freq

        state = self.prepare_state(tokens)
        if not state:
            return 0

        freq_a, list_type_a, pos_a = state[0]
        freq_b, list_type_b, pos_b = state[1]
        list_a = BlockSkipListExt.of(freq_a, list_type_a, self.mmap, pos_a)
        list_b = BlockSkipListExt.of(freq_b, list_type_b, self.mmap, pos_b)
        list_pos_a = list_a.intersection(list_b)
        # find common doc ids
        for freq_b, list_type_b, pos_b in state[2:]:
            list_b = BlockSkipListExt.of(freq_b, list_type_b, self.mmap, pos_b)
            list_pos_a = list_b.intersection_with_doc_ids(self.mmap, list_pos_a)
        return len(list_pos_a)

    def clear(self):
        self.raw_data = {}
        self.data = {}
        self.ndoc = 0

    def get_ndoc(self):
        return self.ndoc
