import math
import os
from array import array


SKIPLIST_P = int(os.environ.get('PYSEARCHLITE_SKIPLIST_P', '8'))
SKIPLIST_MAX_LEVEL = int(os.environ.get('PYSEARCHLITE_SKIPLIST_MAX_LEVEL', '10'))


class BlockSkipList(object):

    def __init__(self):
        self.p = SKIPLIST_P
        self.max_level = 0
        self.blocks = None
        self.last_block = None
        self.last_pos = None
        self.last_id = None

    @staticmethod
    def from_list(ids: list[int], p=SKIPLIST_P, max_level=SKIPLIST_MAX_LEVEL):
        if len(ids) == 1:
            return SingleDocId(ids[0])
        elif len(ids) <= p:
            return DocIdList(ids)

        max_level = min(int(math.log(max(len(ids) - 1, 1), p)), max_level)

        # Start from the fist element.
        blocks = [[ids[0]]]
        # Prepare the first block of each level.
        for i in range(0, max_level):
            # the first value and the index of one level down block
            blocks.append([ids[0], i])

        current_block = [i for i in range(max_level + 1)]

        for i in range(1, len(ids)):
            level = 0
            block = blocks[current_block[0]]
            if len(block) < p:
                block.append(ids[i])
            else:
                new_block = len(blocks)
                block.append(new_block)  # set the pointer to the new block
                blocks.append([ids[i]])  # new block
                current_block[0] = new_block
                # skip list
                while level < max_level:
                    level += 1
                    skip_list_block = blocks[current_block[level]]
                    if len(skip_list_block) < p * 2:
                        skip_list_block.append(ids[i])
                        skip_list_block.append(current_block[level - 1])
                        break
                    new_block = len(blocks)
                    skip_list_block.append(new_block)  # set the pointer to the new block
                    blocks.append([ids[i], current_block[level - 1]])  # new block
                    current_block[level] = new_block

        s = BlockSkipList()
        s.p = p
        s.max_level = max_level
        s.blocks = [array('i', block) for block in blocks]
        return s

    def get_ids(self):
        block = self.blocks[0]
        pos = 0
        result = array('i')
        while True:
            if pos == len(block):  # end of ids
                break
            if pos == self.p:
                block = self.blocks[block[pos]]
                pos = 0
            result.append(block[pos])
            pos += 1
        return result

    def search(self, doc_id_a: int):
        # Check the start position.
        for level in range(self.max_level + 1):
            if doc_id_a <= self.last_id[level]:
                break
        last_block = self.last_block[level]
        block = self.blocks[last_block]
        pos = self.last_pos[level]
        last_pos = pos
        # When the first item is greater than the given doc id.
        if block[pos] >= doc_id_a:
            return block[pos]

        # skip list
        while level > 0:
            while True:
                pos_id = block[pos]
                if pos_id < doc_id_a:
                    last_pos = pos
                    pos += 2
                    if pos >= len(block):  # reach to the end of this level
                        pos = last_pos
                        self.last_pos[level] = last_pos
                        self.last_id[level] = pos_id
                        break  # down the level
                    elif pos >= self.p * 2:  # reach to the end of the block
                        next_block_idx = block[pos]
                        next_block = self.blocks[next_block_idx]
                        next_block0 = next_block[0]
                        if next_block0 > doc_id_a:
                            pos = last_pos
                            self.last_pos[level] = last_pos
                            self.last_id[level] = next_block0
                            break  # down the level
                        self.last_block[level] = next_block_idx
                        block = next_block
                        pos = 0
                elif pos_id > doc_id_a:
                    pos = last_pos
                    self.last_pos[level] = last_pos
                    self.last_id[level] = pos_id
                    break  # down the level
                else:  # pos_id == doc_id_a:
                    self.last_pos[level] = pos
                    self.last_id[level] = pos_id
                    return pos_id
            level -= 1
            self.last_block[level] = block[pos + 1]
            block = self.blocks[block[pos + 1]]
            self.last_pos[level] = 0
            pos = 0

        # ids
        while True:
            pos_id = block[pos]
            if pos_id < doc_id_a:
                next_pos = pos + 1
                if next_pos >= len(block):  # reach to the end of id list
                    self.last_pos[0] = pos
                    self.last_id[0] = pos_id
                    return pos_id
                elif next_pos >= self.p:  # reach to the end of the block
                    next_block_idx = block[next_pos]
                    block = self.blocks[next_block_idx]
                    self.last_block[0] = next_block_idx
                    pos = 0
                else:
                    pos = next_pos
            else:  # pos_id >= doc_id_a
                self.last_pos[0] = pos
                self.last_id[0] = pos_id
                return pos_id

    def intersection(self, b) -> array:
        block = self.blocks[0]
        pos = 0
        b.reset()
        result = array('i')
        while True:
            if pos == len(block):  # end of ids
                break
            if pos == self.p:
                block = self.blocks[block[pos]]
                pos = 0
            doc_id_a = block[pos]
            doc_id_b = b.search(doc_id_a)
            if doc_id_b < doc_id_a:  # reached to the end of b
                break
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
            pos += 1
        return result

    def intersection_with_doc_ids(self, a: array) -> array:
        self.reset()
        result = array('i')
        for doc_id_a in a:
            doc_id_b = self.search(doc_id_a)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
        return result

    def reset(self):
        self.last_block = [i for i in range(self.max_level + 1)]
        self.last_pos = [0] * (self.max_level + 1)
        self.last_id = [-1] * (self.max_level + 1)


class DocIdList(object):

    def __init__(self, ids):
        self.ids = array('i', ids)
        self.current_pos = 0

    def get_ids(self) -> list[int]:
        return self.ids.tolist()

    def search(self, doc_id_a: int):
        for i in range(self.current_pos, len(self.ids)):
            if self.ids[i] >= doc_id_a:
                self.current_pos = i
                return self.ids[i]
        return self.ids[-1]

    def intersection(self, b) -> array:
        b.reset()
        result = array('i')
        # assume a < b
        for doc_id_a in self.ids:
            doc_id_b = b.search(doc_id_a)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
        return result

    def intersection_with_doc_ids(self, a: array) -> array:
        self.reset()
        result = array('i')
        # assume a < b
        for doc_id_a in a:
            doc_id_b = self.search(doc_id_a)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
        return result

    def reset(self):
        self.current_pos = 0


class SingleDocId(object):

    def __init__(self, doc_id):
        self.doc_id = doc_id

    def get_ids(self) -> list[int]:
        return [self.doc_id]

    def search(self, doc_id_a: int):
        # it can return a smaller id than id_a.
        return self.doc_id

    def intersection(self, b) -> array:
        # assume a < b
        b.reset()
        doc_id_b = b.search(self.doc_id)
        result = array('i')
        if doc_id_b == self.doc_id:
            result.append(doc_id_b)
        return result

    def intersection_with_doc_ids(self, a: array) -> array:
        result = array('i')
        # assume a < this. so len(a) should be 1.
        for doc_id_a in a:
            if self.doc_id == doc_id_a:
                result.append(doc_id_a)
        return result

    def reset(self):
        pass
