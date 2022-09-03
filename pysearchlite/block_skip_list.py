import os
import sys

from pysearchlite.gamma_codecs import (
    BLOCK_TYPE_DOC_ID,
    BLOCK_TYPE_DOC_IDS_LIST,
    BLOCK_TYPE_SKIP_LIST,
    DOCID_LEN_BYTES,
    SKIP_LIST_BLOCK_INDEX_BYTES,
    bytes_docid,
    compare_docid,
    decode_block_idx,
    encode_block_idx,
    encode_docid,
    bytes_block_idx,
    write_block_skip_list,
    write_doc_ids_list,
    write_single_doc_id,
)

SKIPLIST_BLOCK_SIZE = int(os.environ.get('PYSEARCHLITE_SKIPLIST_BLOCK_SIZE', '44'))
SKIPLIST_MAX_LEVEL = int(os.environ.get('PYSEARCHLITE_SKIPLIST_MAX_LEVEL', '10'))

LIST_TYPE_DOC_ID = 1
LIST_TYPE_DOC_IDS_LIST = 2
LIST_TYPE_SKIP_LIST = 3


class BlockSkipList(object):

    def __init__(self):
        self.block_size = SKIPLIST_BLOCK_SIZE
        self.max_level = 0
        self.blocks = None
        self.next_block_idx = None
        self.level_block_idx = None
        self.freq = 0

    @staticmethod
    def from_list(ids, block_size=SKIPLIST_BLOCK_SIZE, max_level=SKIPLIST_MAX_LEVEL):
        """
        Return a BlockSkipList, DocIdList, or SingleDocId from the given ids.

        Parameters
        ----------
        ids: list[int]
            a list of doc ids
        block_size: int, default SKIPLIST_BLOCK_SIZE
            the size of block
        max_level: int, default SKIPLIST_MAX_LEVEL
            the maximum level of skip list

        Returns
        -------
        list: BlockSkipList, DocIdList, or SingleDocId
        """
        if len(ids) == 1:
            return SingleDocId(ids[0])

        # Start from the fist element.
        doc_id = encode_docid(ids[0])
        blocks = [bytearray(doc_id)]
        next_block_idx = [0]

        current_block_idx = [0]
        level_block_idx = [0]

        def add_new_block(content):
            idx = len(blocks)
            blocks.append(content)
            next_block_idx.append(0)
            return idx

        for i in range(1, len(ids)):
            level = 0
            block = blocks[current_block_idx[0]]
            doc_id = encode_docid(ids[i])
            if len(block) + len(doc_id) + 1 + SKIP_LIST_BLOCK_INDEX_BYTES <= block_size:
                block.extend(doc_id)
            else:
                new_block_idx = add_new_block(bytearray(doc_id))
                next_block_idx[current_block_idx[0]] = new_block_idx
                current_block_idx[0] = new_block_idx
                # skip list
                while level < max_level:
                    level += 1
                    if len(current_block_idx) <= level:
                        # new level
                        new_block_idx = add_new_block(
                            bytearray(encode_docid(ids[0]) + encode_block_idx(level_block_idx[level - 1])))
                        level_block_idx.append(new_block_idx)
                        current_block_idx.append(new_block_idx)
                    skip_list_block = blocks[current_block_idx[level]]
                    lower_level_idx_enc = encode_block_idx(current_block_idx[level - 1])
                    if (len(skip_list_block) + len(doc_id) + len(lower_level_idx_enc)
                            + 1 + SKIP_LIST_BLOCK_INDEX_BYTES) <= block_size:
                        skip_list_block.extend(doc_id)
                        skip_list_block.extend(lower_level_idx_enc)
                        break
                    # new block for skip list
                    new_block_idx = add_new_block(bytearray(doc_id + lower_level_idx_enc))
                    next_block_idx[current_block_idx[level]] = new_block_idx
                    current_block_idx[level] = new_block_idx

        if len(level_block_idx) == 1:
            # TODO maybe we can generate DocIdList directly from blocks
            return DocIdList(ids)

        s = BlockSkipList()
        s.block_size = block_size
        s.max_level = len(level_block_idx) - 1
        s.blocks = blocks
        s.level_block_idx = level_block_idx
        s.next_block_idx = next_block_idx
        s.freq = len(ids)
        return s

    def write(self, file):
        write_block_skip_list(self, file)


class BlockSkipListExt(object):

    def __init__(self, mmap, pos, freq):
        self.mmap = mmap
        # block_size(1) max_level(1) level_block_idx[max_level] num_blocks
        self.block_size = int.from_bytes(mmap[pos:pos+1], sys.byteorder)
        self.max_level = int.from_bytes(mmap[pos+1:pos+2], sys.byteorder)
        self.level_block_idx = [0]
        for i in range(self.max_level):
            p = pos + 2 + i * SKIP_LIST_BLOCK_INDEX_BYTES
            self.level_block_idx.append(int.from_bytes(mmap[p:p + SKIP_LIST_BLOCK_INDEX_BYTES], sys.byteorder))
        self.offset = pos + 2 + self.max_level * SKIP_LIST_BLOCK_INDEX_BYTES + SKIP_LIST_BLOCK_INDEX_BYTES
        self.freq = freq

    @staticmethod
    def of(freq, list_type, mem, pos):
        if list_type == LIST_TYPE_DOC_ID:
            return SingleDocIdExt(mem, pos)
        elif list_type == LIST_TYPE_DOC_IDS_LIST:
            return DocIdListExt(mem, pos, freq)
        elif list_type == LIST_TYPE_SKIP_LIST:
            return BlockSkipListExt(mem, pos, freq)

    @staticmethod
    def read(mem):
        block_type = mem[0:1]  # TODO
        if block_type == BLOCK_TYPE_DOC_ID:
            return SingleDocIdExt(mem, 1)
        elif block_type == BLOCK_TYPE_DOC_IDS_LIST:
            freq = int.from_bytes(mem[1:DOCID_LEN_BYTES + 1], sys.byteorder)
            return DocIdListExt(mem, DOCID_LEN_BYTES + 1, freq)
        elif block_type == BLOCK_TYPE_SKIP_LIST:
            freq = int.from_bytes(mem[1:DOCID_LEN_BYTES + 1], sys.byteorder)
            return BlockSkipListExt(mem, DOCID_LEN_BYTES + 1, freq)
        else:
            raise ValueError(f"Unsupported block type: {block_type}")

    def get_iter(self):
        return BlockSkipListExtIter(self)

    def get_ids(self):
        block_offset = self.offset
        block_size = self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES]
        pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
        block_end = pos + block_size
        result = []
        while True:
            if pos >= block_end:
                block_idx = int.from_bytes(
                    self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES], sys.byteorder)
                if block_idx == 0:
                    break
                block_offset = self.offset + self.block_size * block_idx
                block_size = self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES]
                pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                block_end = pos + block_size
            result.append(pos)
            pos += bytes_docid(self.mmap, pos)
        return result

    def intersection(self, b):
        a_iter = self.get_iter()
        pos_a = a_iter.last_pos[0]
        b_iter = b.get_iter()
        result = []
        while True:
            pos_b, cmp = b_iter.search(self.mmap, pos_a)
            if cmp == 0:
                result.append(pos_a)
                pos_a, cmp = a_iter.next_pos()
                if cmp < 0:  # reached to the end of a
                    break
            elif cmp < 0:  # reached to the end of b
                break
            else:
                pos_a, cmp = a_iter.search(b.mmap, pos_b)
                if cmp == 0:
                    result.append(pos_a)
                    pos_a, cmp = a_iter.next_pos()
                    if cmp < 0:  # reached to the end of a
                        break
                elif cmp < 0:  # reached to the end of a
                    break
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        i = self.get_iter()
        result = []
        for pos_a in list_pos_a:
            pos_b, cmp = i.search(mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
            elif cmp < 0:  # reached to the end of b
                break
        return result


class BlockSkipListExtIter(object):

    def __init__(self, block_skip_list):
        self.list = block_skip_list
        self.mmap = block_skip_list.mmap
        self.last_block_idx = [block_skip_list.level_block_idx[i] for i in range(block_skip_list.max_level + 1)]
        self.last_pos = [self._get_block_offset(block_skip_list.level_block_idx[i]) + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                         for i in range(block_skip_list.max_level + 1)]
        self.last_cmp_pos = self.last_pos[:]
        self.last_level = block_skip_list.max_level

    def _get_block_offset(self, idx):
        return self.list.offset + self.list.block_size * idx

    def _get_first_pos(self, block_offset):
        return block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1

    def _get_block_end(self, block_offset):
        return self._get_first_pos(block_offset) + self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES]

    def _get_next_block_idx(self, block_offset):
        return int.from_bytes(self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES], sys.byteorder)

    def search(self, mem_a, pos_a):
        # Check the start position.
        level = self.last_level
        while level < self.list.max_level:
            if compare_docid(self.mmap, self.last_cmp_pos[level + 1], mem_a, pos_a) >= 0:
                break
            level += 1
        block_idx = self.last_block_idx[level]
        block_offset = self._get_block_offset(block_idx)
        block_end = self._get_block_end(block_offset)
        pos = self.last_pos[level]
        last_block_idx = block_idx
        last_pos = pos

        # skip list
        while level > 0:
            while True:
                cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
                if cmp < 0:
                    last_block_idx = block_idx
                    last_pos = pos
                    pos += bytes_docid(self.mmap, pos)
                    pos += bytes_block_idx(self.mmap, pos)
                    if pos >= block_end:  # reached to the end of the block
                        block_idx = self._get_next_block_idx(block_offset)
                        if block_idx == 0:  # reached to the end of this level
                            self.last_block_idx[level] = last_block_idx
                            self.last_cmp_pos[level] = last_pos
                            self.last_pos[level] = last_pos
                            pos = last_pos
                            break  # down the level
                        block_offset = self._get_block_offset(block_idx)
                        block_end = self._get_block_end(block_offset)
                        pos = self._get_first_pos(block_offset)
                elif cmp > 0:
                    self.last_block_idx[level] = last_block_idx
                    self.last_cmp_pos[level] = pos
                    self.last_pos[level] = last_pos
                    pos = last_pos
                    break  # down the level
                else:  # cmp == 0:
                    self.last_block_idx[level] = block_idx
                    self.last_cmp_pos[level] = pos
                    self.last_pos[level] = pos
                    self.last_level = level
                    return pos, cmp
            level -= 1
            pos += bytes_docid(self.mmap, pos)
            block_idx = decode_block_idx(self.mmap, pos)
            block_offset = self._get_block_offset(block_idx)
            block_end = self._get_block_end(block_offset)
            pos = self._get_first_pos(block_offset)

        # ids
        while True:
            cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
            if cmp < 0:
                last_block_idx = block_idx
                last_pos = pos
                pos += bytes_docid(self.mmap, pos)
                if pos >= block_end:  # reach to the end of the block
                    block_idx = self._get_next_block_idx(block_offset)
                    if block_idx == 0:  # reached to the end of id list
                        self.last_block_idx[0] = last_block_idx
                        self.last_pos[0] = last_pos
                        self.last_level = 0
                        return last_pos, cmp
                    block_offset = self._get_block_offset(block_idx)
                    block_end = self._get_block_end(block_offset)
                    pos = self._get_first_pos(block_offset)
            else:  # cmp >= 0
                self.last_block_idx[0] = block_idx
                self.last_pos[0] = pos
                self.last_level = 0
                return pos, cmp

    def next_pos(self):
        level = self.last_level
        block_idx = self.last_block_idx[level]
        block_offset = self._get_block_offset(block_idx)
        pos = self.last_pos[level]
        while level > 0:
            pos += bytes_docid(self.mmap, pos)
            block_idx = decode_block_idx(self.mmap, pos)
            block_offset = self._get_block_offset(block_idx)
            pos = self._get_first_pos(block_offset)
            level -= 1
            self.last_block_idx[level] = block_idx
            self.last_cmp_pos[level] = pos
            self.last_pos[level] = pos

        pos += bytes_docid(self.mmap, pos)
        block_end = self._get_block_end(block_offset)
        if pos >= block_end:  # reach to the end of the block
            block_idx = self._get_next_block_idx(block_offset)
            if block_idx == 0:  # reached to the end of id list
                return self.last_pos[0], -1
            block_offset = self._get_block_offset(block_idx)
            pos = self._get_first_pos(block_offset)
            self.last_block_idx[0] = block_idx
        self.last_pos[0] = pos
        self.last_level = 0
        return pos, 1


class DocIdList(object):

    def __init__(self, ids):
        self.ids = [encode_docid(doc_id) for doc_id in ids]
        self.current_pos = 0

    def write(self, file):
        write_doc_ids_list(self, file)


class DocIdListExt(object):

    def __init__(self, mmap, offset, freq):
        self.freq = freq
        self.mmap = mmap
        self.offset = offset

    def get_iter(self):
        return DocIdListExtIter(self)

    def get_ids(self):
        pos = self.offset
        result = []
        for _ in range(self.freq):
            result.append(pos)
            pos += bytes_docid(self.mmap, pos)
        return result

    def intersection(self, b):
        pos = self.offset
        b_iter = b.get_iter()
        result = []
        # assume len(a) < len(b)
        for i in range(self.freq):
            pos_b, cmp = b_iter.search(self.mmap, pos)
            if cmp == 0:
                result.append(pos)
            elif cmp < 0:  # reach to the end of list
                break
            pos += bytes_docid(self.mmap, pos)
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        i = self.get_iter()
        result = []
        # assume len(a) < len(b)
        for pos_a in list_pos_a:
            pos_b, cmp = i.search(mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
            elif cmp < 0:  # reach to the end of list
                break
        return result


class DocIdListExtIter(object):

    def __init__(self, doc_id_list):
        self.list = doc_id_list
        self.mmap = doc_id_list.mmap
        self.current_idx = 0
        self.current_pos = doc_id_list.offset

    def search(self, mem_a, pos_a):
        i = self.current_idx
        pos = self.current_pos
        while True:
            cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
            if cmp >= 0:
                self.current_idx = i
                self.current_pos = pos
                return pos, cmp
            i += 1
            if i >= self.list.freq:
                self.current_idx = i - 1
                self.current_pos = pos
                return pos, -1
            pos += bytes_docid(self.mmap, pos)

    def next_pos(self):
        i = self.current_idx + 1
        if i >= self.list.freq:
            return self.current_pos, -1
        self.current_pos += bytes_docid(self.mmap, self.current_pos)
        self.current_idx = i
        return self.current_pos, 1


class SingleDocId(object):

    def __init__(self, doc_id):
        self.doc_id = encode_docid(doc_id)

    def write(self, file):
        write_single_doc_id(self.doc_id, file)


class SingleDocIdExt(object):

    def __init__(self, mmap, offset):
        self.mmap = mmap
        self.offset = offset

    def get_iter(self):
        return SingleDocIdExtIter(self)

    def get_ids(self):
        return [self.offset]

    def intersection(self, b):
        # assume a < b
        i = b.get_iter()
        pos_b, cmp = i.search(self.mmap, self.offset)
        result = []
        if cmp == 0:
            result.append(self.offset)
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        result = []
        # assume a < this. so len(a) should be 1.
        for pos_a in list_pos_a:
            cmp = compare_docid(self.mmap, self.offset, mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
            else:
                break
        return result


class SingleDocIdExtIter(object):

    def __init__(self, single_doc_id):
        self.sdi = single_doc_id

    def search(self, mem_a, pos_a):
        cmp = compare_docid(self.sdi.mmap, self.sdi.offset, mem_a, pos_a)
        return self.sdi.offset, cmp

    def next_pos(self):
        return self.sdi.offset, -1
