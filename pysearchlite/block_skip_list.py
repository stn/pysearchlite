import os
import sys

from pysearchlite.gamma_codecs import SKIP_LIST_BLOCK_INDEX_BYTES, BLOCK_TYPE_DOC_ID, \
    BLOCK_TYPE_DOC_IDS_LIST, BLOCK_TYPE_SKIP_LIST, DOCID_LEN_BYTES, encode_docid, encode_block_idx, decode_block_idx, \
    compare_docid, is_zero_docid, write_single_doc_id, bytes_docid, write_doc_ids_list, write_block_skip_list

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
        if len(ids) == 1:
            return SingleDocId(ids[0])

        # Start from the fist element.
        doc_id = encode_docid(ids[0])
        blocks = [bytearray(doc_id)]
        next_block_idx = [0]
        block_freq = [1]

        current_block_idx = [0]
        level_block_idx = [0]

        for i in range(1, len(ids)):
            level = 0
            block = blocks[current_block_idx[0]]
            doc_id = encode_docid(ids[i])
            if len(block) + len(doc_id) + 1 + SKIP_LIST_BLOCK_INDEX_BYTES <= block_size:
                block.extend(doc_id)
                block_freq[current_block_idx[0]] += 1
            else:
                new_block_idx = len(blocks)
                next_block_idx[current_block_idx[0]] = new_block_idx
                blocks.append(bytearray(doc_id))  # new block
                next_block_idx.append(0)
                block_freq.append(1)
                current_block_idx[0] = new_block_idx
                # skip list
                while level < max_level:
                    level += 1
                    if len(current_block_idx) <= level:
                        new_block_idx = len(blocks)
                        docid0 = encode_docid(ids[0])
                        blocks.append(bytearray(docid0 + encode_block_idx(level_block_idx[level - 1])))
                        level_block_idx.append(new_block_idx)
                        next_block_idx.append(0)
                        block_freq.append(1)
                        current_block_idx.append(new_block_idx)
                    skip_list_block = blocks[current_block_idx[level]]
                    if len(skip_list_block) + len(doc_id) + 1 + SKIP_LIST_BLOCK_INDEX_BYTES * 2 <= block_size:
                        skip_list_block.extend(doc_id)
                        skip_list_block.extend(encode_block_idx(current_block_idx[level - 1]))
                        block_freq[current_block_idx[level]] += 1
                        break
                    new_block_idx = len(blocks)
                    next_block_idx[current_block_idx[level]] = new_block_idx
                    blocks.append(bytearray(doc_id + encode_block_idx(current_block_idx[level - 1])))  # new block
                    next_block_idx.append(0)
                    block_freq.append(1)
                    current_block_idx[level] = new_block_idx

        if len(level_block_idx) == 1:
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
        self.last_block_idx = None
        self.last_pos = None
        self.last_cmp_pos = None
        self.last_i = None
        #self.last_id = None

    @staticmethod
    def of(freq, list_type, mem, pos):
        if list_type == LIST_TYPE_DOC_ID:
            return SingleDocIdExt(mem, pos)
        elif list_type == LIST_TYPE_DOC_IDS_LIST:
            return DocIdListExt(mem, pos, freq)
        elif list_type == LIST_TYPE_SKIP_LIST:
            return BlockSkipListExt(mem, pos, freq)

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

    def get_ids(self):
        block_offset = self.offset
        block_size = self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES]
        pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
        block_end = pos + block_size
        result = []
        while True:
            if pos >= block_end:
                block_idx = decode_block_idx(self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                if block_idx == 0:
                    break
                block_offset = self.offset + self.block_size * block_idx
                block_size = self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES]
                pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                block_end = pos + block_size
            result.append(pos)
            pos += bytes_docid(self.mmap, pos)
        return result

    def search(self, mem_a, pos_a):
        # Check the start position.
        for level in range(self.max_level + 1):
            if compare_docid(self.mmap, self.last_cmp_pos[level], mem_a, pos_a) >= 0:
                break
        block_idx = self.last_block_idx[level]
        block_offset = self.offset + self.block_size * block_idx
        block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                     self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
        pos = self.last_pos[level]
        last_pos = pos

        # skip list
        while level > 0:
            while True:
                cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
                if cmp < 0:
                    last_pos = pos
                    pos += bytes_docid(self.mmap, pos) + SKIP_LIST_BLOCK_INDEX_BYTES
                    if pos >= block_end:  # reached to the end of the block
                        next_block_idx = decode_block_idx(
                            self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                        if next_block_idx == 0:  # reached to the end of this level
                            self.last_cmp_pos[level] = last_pos
                            self.last_pos[level] = last_pos
                            pos = last_pos
                            break  # down the level
                        next_block_offset = self.offset + self.block_size * next_block_idx
                        next_pos0 = next_block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                        if compare_docid(self.mmap, next_pos0, mem_a, pos_a) > 0:
                            self.last_cmp_pos[level] = next_pos0
                            self.last_pos[level] = last_pos
                            pos = last_pos
                            break  # down the level
                        block_idx = next_block_idx
                        block_offset = next_block_offset
                        block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                                     self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                        pos = next_pos0
                        self.last_block_idx[level] = block_idx
                elif cmp > 0:
                    self.last_cmp_pos[level] = pos
                    self.last_pos[level] = last_pos
                    pos = last_pos
                    break  # down the level
                else:  # cmp == 0:
                    self.last_cmp_pos[level] = pos
                    self.last_pos[level] = pos
                    return pos, cmp
            level -= 1
            pos += bytes_docid(self.mmap, pos)
            block_idx = decode_block_idx(self.mmap[pos:pos + SKIP_LIST_BLOCK_INDEX_BYTES])
            block_offset = self.offset + self.block_size * block_idx
            block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                         self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
            pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
            self.last_block_idx[level] = block_idx
            self.last_pos[level] = pos

        # ids
        while True:
            cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
            if cmp < 0:
                next_pos = pos + bytes_docid(self.mmap, pos)
                if next_pos >= block_end:  # reach to the end of the block
                    next_block_idx = decode_block_idx(
                        self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                    if next_block_idx == 0:  # reached to the end of id list
                        self.last_cmp_pos[0] = pos
                        self.last_pos[0] = pos
                        return pos, cmp
                    block_offset = self.offset + self.block_size * next_block_idx
                    block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                                 self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                    pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                    self.last_block_idx[0] = next_block_idx
                else:
                    pos = next_pos
            else:  # cmp >= 0
                self.last_cmp_pos[0] = pos
                self.last_pos[0] = pos
                return pos, cmp

    def intersection(self, b):
        block_offset = self.offset
        block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                     self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
        pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
        b.reset()
        result = []
        while True:
            if pos >= block_end:
                block_idx = decode_block_idx(self.mmap[block_offset:block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                if block_idx == 0:
                    break
                block_offset = self.offset + self.block_size * block_idx
                block_end = (block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1 +
                             self.mmap[block_offset + SKIP_LIST_BLOCK_INDEX_BYTES])
                pos = block_offset + SKIP_LIST_BLOCK_INDEX_BYTES + 1
            pos_b, cmp = b.search(self.mmap, pos)
            if cmp == 0:
                result.append(pos)
            elif cmp < 0:  # reached to the end of b
                break
            pos += bytes_docid(self.mmap, pos)
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        self.reset()
        result = []
        for pos_a in list_pos_a:
            pos_b, cmp = self.search(mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
            if cmp < 0:  # reached to the end of b
                break
        return result

    def reset(self):
        self.last_block_idx = [self.level_block_idx[i] for i in range(self.max_level + 1)]
        self.last_pos = [self.offset + self.block_size * self.level_block_idx[i] + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                         for i in range(self.max_level + 1)]
        self.last_cmp_pos = self.last_pos[:]


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
        self.current_idx = 0
        self.current_pos = offset

    def get_ids(self):
        pos = self.offset
        result = []
        for _ in range(self.freq):
            result.append(pos)
            pos += bytes_docid(self.mmap, pos)
        return result

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
            if i >= self.freq:
                break
            pos += bytes_docid(self.mmap, pos)
        return pos, cmp

    def intersection(self, b):
        pos = self.offset
        b.reset()
        result = []
        # assume len(a) < len(b)
        for i in range(self.freq):
            pos_b, cmp = b.search(self.mmap, pos)
            if cmp == 0:
                result.append(pos)
            pos += bytes_docid(self.mmap, pos)
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        self.reset()
        result = []
        # assume len(a) < len(b)
        for pos_a in list_pos_a:
            pos_b, cmp = self.search(mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
        return result

    def reset(self):
        self.current_idx = 0
        self.current_pos = self.offset


class SingleDocId(object):

    def __init__(self, doc_id):
        self.doc_id = encode_docid(doc_id)

    def write(self, file):
        write_single_doc_id(self.doc_id, file)


class SingleDocIdExt(object):

    def __init__(self, mmap, offset):
        self.mmap = mmap
        self.offset = offset

    def get_ids(self):
        return [self.offset]

    def search(self, mem_a, pos_a):
        # it can return a smaller id than id_a.
        cmp = compare_docid(self.mmap, self.offset, mem_a, pos_a)
        return self.offset, cmp

    def intersection(self, b):
        # assume a < b
        b.reset()
        pos_b, cmp = b.search(self.mmap, self.offset)
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
        return result

    def reset(self):
        pass
