import os
import sys

from pysearchlite.gamma_codecs import SKIP_LIST_BLOCK_INDEX_BYTES, BLOCK_TYPE_DOC_ID, \
    BLOCK_TYPE_DOC_IDS_LIST, BLOCK_TYPE_SKIP_LIST, DOCID_LEN_BYTES, encode_docid, encode_block_idx, decode_block_idx, \
    compare_docid, is_zero_docid, write_single_doc_id, docid_bytes, write_doc_ids_list, write_block_skip_list

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
        self.block_freq = None
        self.level_block_idx = None
        self.freq = 0
        self.last_block_idx = None
        self.last_pos = None
        self.last_id = None

    @staticmethod
    def from_list(ids, block_size=SKIPLIST_BLOCK_SIZE, max_level=SKIPLIST_MAX_LEVEL):
        if len(ids) == 1:
            return SingleDocId(ids[0])
        #elif len(ids) <= p:
        #    return DocIdList(ids)

        #max_level = min(int(math.log(max(len(ids) - 1, 1), p)), max_level)

        # Start from the fist element.
        doc_id = encode_docid(ids[0])
        blocks = [bytearray(doc_id)]
        next_block_idx = [0]
        block_freq = [1]
        ## Prepare the first block of each level.
        #for i in range(0, max_level):
        #    # the first value and the index of one level down block
        #    blocks.append([doc_id, encode_block_idx(i)])
        #    next_block_idx.append(0)

        #current_block = [i for i in range(max_level + 1)]
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
        s.block_freq = block_freq
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

    def get_ids(self):
        block_pos = self.offset
        pos = SKIP_LIST_BLOCK_INDEX_BYTES + 1
        i = 0
        freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
        result = []
        while True:
            if i >= freq:
                block_idx = decode_block_idx(self.mmap[block_pos:block_pos + SKIP_LIST_BLOCK_INDEX_BYTES])
                if block_idx == 0:
                    break
                block_pos = self.offset + self.block_size * block_idx
                pos = SKIP_LIST_BLOCK_INDEX_BYTES + 1
                i = 0
                freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
            pos_a = block_pos + pos
            if is_zero_docid(self.mmap, pos_a):
                break
            result.append(pos_a)
            pos += docid_bytes(self.mmap, pos_a)
            i += 1
        return result

    def search(self, mem_a, pos_a):
        # Check the start position.
        for level in range(self.max_level + 1):
            #if doc_id_a <= self.last_id[level]:
            if compare_docid(self.mmap, self.last_pos[level], mem_a, pos_a) >= 0:
                break
        block_idx = self.last_block_idx[level]
        block_pos = self.offset + self.block_size * block_idx
        pos = self.last_pos[level]
        i = self.last_i[level]
        freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
        last_pos = pos
        last_i = i
        # When the first item is greater than the given doc id.
        #pos_id = self.mmap[block_pos + pos: block_pos + pos + DOCID_BYTES]
        #if pos_id >= doc_id_a:
        #    return pos_id
        cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
        if cmp >= 0:
            return pos, cmp

        # skip list
        while level > 0:
            while True:
                #pos_id = self.mmap[block_pos + pos: block_pos + pos + DOCID_BYTES]
                #if pos_id < doc_id_a:
                cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
                if cmp < 0:
                    last_pos = pos
                    last_i = i
                    pos += docid_bytes(self.mmap, pos) + SKIP_LIST_BLOCK_INDEX_BYTES
                    i += 1
                    if i >= freq:  # reached to the end of the block
                        next_block_idx = decode_block_idx(self.mmap[block_pos:block_pos + SKIP_LIST_BLOCK_INDEX_BYTES])
                        if next_block_idx == 0:  # reached to the end of this level
                            pos = last_pos
                            self.last_pos[level] = last_pos
                            self.last_i[level] = last_i
                            #self.last_id[level] = pos_id
                            break  # down the level
                        next_block_pos = self.offset + self.block_size * next_block_idx
                        #next_block0 = self.mmap[next_block_pos + SKIP_LIST_BLOCK_INDEX_BYTES:next_block_pos + SKIP_LIST_BLOCK_INDEX_BYTES + DOCID_BYTES]
                        #if next_block0 > doc_id_a:
                        next_pos0 = next_block_pos + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                        if compare_docid(self.mmap, next_pos0, mem_a, pos_a) > 0:
                            pos = last_pos
                            self.last_pos[level] = last_pos
                            self.last_i[level] = last_i
                            #self.last_id[level] = next_block0
                            break  # down the level
                        #block = next_block
                        block_idx = next_block_idx
                        block_pos = next_block_pos
                        pos = next_pos0
                        i = 0
                        freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
                        self.last_block_idx[level] = block_idx
                #elif pos_id > doc_id_a:
                elif cmp > 0:
                    pos = last_pos
                    self.last_pos[level] = last_pos
                    self.last_i[level] = last_i
                    #self.last_id[level] = pos_id
                    break  # down the level
                else:  # cmp == 0:
                    self.last_pos[level] = pos
                    self.last_i[level] = last_i
                    #self.last_id[level] = pos_id
                    return pos, cmp
            level -= 1
            pos += docid_bytes(self.mmap, pos)
            block_idx = decode_block_idx(self.mmap[pos:pos + SKIP_LIST_BLOCK_INDEX_BYTES])
            self.last_block_idx[level] = block_idx
            block_pos = self.offset + self.block_size * block_idx
            self.last_pos[level] = SKIP_LIST_BLOCK_INDEX_BYTES + 1
            self.last_i[level] = 0
            pos = block_pos + SKIP_LIST_BLOCK_INDEX_BYTES + 1
            i = 0
            freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]

        # ids
        while True:
            #pos_id = self.mmap[block_pos + pos: block_pos + pos + DOCID_BYTES]
            #if pos_id < doc_id_a:
            cmp = compare_docid(self.mmap, pos, mem_a, pos_a)
            if cmp < 0:
                next_pos = pos + docid_bytes(self.mmap, pos)
                i += 1
                if i >= freq:  # reach to the end of the block
                    next_block_idx = decode_block_idx(self.mmap[block_pos:block_pos + SKIP_LIST_BLOCK_INDEX_BYTES])
                    if next_block_idx == 0:  # reached to the end of id list
                        pos = last_pos
                        self.last_pos[0] = pos
                        self.last_i[0] = i - 1
                        #self.last_id[0] = pos_id
                        return pos, cmp
                    block_pos = self.offset + self.block_size * next_block_idx
                    self.last_block_idx[0] = next_block_idx
                    pos = block_pos + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                    i = 0
                    freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
                else:
                    pos = next_pos
            else:  # cmp >= 0
                self.last_pos[0] = pos
                self.last_i[0] = i
                #self.last_id[0] = pos_id
                return pos, cmp

    def intersection(self, b):
        block_pos = self.offset
        pos = SKIP_LIST_BLOCK_INDEX_BYTES + 1
        i = 0
        freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
        b.reset()
        result = []
        #doc_id_b = b'\x00\x00\x00\x00'
        while True:
            if i >= freq:
                block_idx = decode_block_idx(self.mmap[block_pos:block_pos + SKIP_LIST_BLOCK_INDEX_BYTES])
                if block_idx == 0:
                    break
                block_pos = self.offset + self.block_size * block_idx
                pos = SKIP_LIST_BLOCK_INDEX_BYTES + 1
                i = 0
                freq = self.mmap[block_pos + SKIP_LIST_BLOCK_INDEX_BYTES]
            #if doc_id_a == b'\x00\x00\x00\x00':
            #    break
            pos_a = block_pos + pos
            pos_b, cmp = b.search(self.mmap, pos_a)
            #if doc_id_b == doc_id_a:
            if cmp == 0:
                result.append(pos_a)
            #elif doc_id_b < doc_id_a:  # reached to the end of b
            elif cmp < 0:  # reached to the end of b
                break
            pos += docid_bytes(self.mmap, pos_a)
            i += 1
        return result

    def intersection_with_doc_ids(self, mem_a, list_pos_a):
        self.reset()
        result = []
        for pos_a in list_pos_a:
            #if doc_id_b == doc_id_a:
            pos_b, cmp = self.search(mem_a, pos_a)
            if cmp == 0:
                result.append(pos_a)
            #if doc_id_b < doc_id_a:  # reached to the end of b
            if cmp < 0:  # reached to the end of b
                break
        return result

    def reset(self):
        self.last_block_idx = [self.level_block_idx[i] for i in range(self.max_level + 1)]
        self.last_pos = [self.offset + self.block_size * self.level_block_idx[i] + SKIP_LIST_BLOCK_INDEX_BYTES + 1
                         for i in range(self.max_level + 1)]
        self.last_i = [0] * (self.max_level + 1)
        #self.last_id = [b'\x00\x00\x00\x00'] * (self.max_level + 1)


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
        for i in range(self.freq):
            result.append(pos)
            pos += docid_bytes(self.mmap, pos)
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
            pos += docid_bytes(self.mmap, pos)
        return pos, cmp

    def intersection(self, b):
        pos = self.offset
        b.reset()
        result = []
        # assume len(a) < len(b)
        for i in range(self.freq):
            #doc_id_a = self.mmap[pos:pos + DOCID_BYTES]
            pos_b, cmp = b.search(self.mmap, pos)
            if cmp == 0:
                result.append(pos)
            pos += docid_bytes(self.mmap, pos)
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
