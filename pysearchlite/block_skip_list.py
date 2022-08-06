import math
import os
from array import array


SKIPLIST_P = int(os.environ.get('PYSEARCHLITE_SKIPLIST_P', '9'))
OFFSET = int(os.environ.get('PYSEARCHLITE_SKIPLIST_OFFSET', '5'))


class BlockSkipList(object):

    def __init__(self):
        self.p = SKIPLIST_P
        self.ids = None
        self.skip_lists = None
        self.current_pos = None
        self.last_id = None

    @staticmethod
    def from_list(ids: list[int], p=SKIPLIST_P, offset=OFFSET):
        max_height = math.log(max(len(ids) - 1, 1), p) - offset
        skip_lists = []
        for i in range(1, len(ids)):
            level = 0
            m = p
            while (i % m) == 0 and level < max_height:
                if len(skip_lists) <= level:
                    skip_lists.append([ids[0]])
                skip_lists[level].append(ids[i])
                level += 1
                m *= p
        s = BlockSkipList()
        s.p = p
        s.ids = array('i', ids)
        s.skip_lists = [array('i', sl) for sl in skip_lists]
        return s

    def get_ids(self) -> list[int]:
        return self.ids.tolist()

    def search(self, doc_id_a: int):
        if len(self.skip_lists) == 0:
            # no skip list
            for i in range(self.current_pos[0], len(self.ids)):
                if self.ids[i] >= doc_id_a:
                    self.current_pos[0] = i
                    return self.ids[i]
            return self.ids[-1]

        # Check the start position.
        for level in range(1, len(self.skip_lists) + 1):
            if doc_id_a <= self.last_id[level]:
                break
        pos = self.current_pos[level]
        skip_list = self.skip_lists[level - 1]

        # When the first item is greater than the given doc id.
        if skip_list[pos] >= doc_id_a:
            return skip_list[pos]

        # skip list
        while level > 0:
            while True:
                pos_id = skip_list[pos]
                if pos_id < doc_id_a:
                    pos += 1
                    if pos >= len(skip_list):
                        self.current_pos[level] = pos - 1
                        self.last_id[level] = pos_id
                        break
                elif pos_id > doc_id_a:
                    self.current_pos[level] = pos - 1  # 最初の要素がこうならないようにガードが必要
                    self.last_id[level] = pos_id
                    break
                else:  # pos_id == doc_id_a:
                    self.current_pos[level] = pos
                    self.last_id[level] = pos_id
                    return pos_id
            pos = pos * self.p
            level -= 1
            skip_list = self.skip_lists[level - 1]

        # ids
        for i in range(pos, len(self.ids)):
            pos_id = self.ids[i]
            if pos_id >= doc_id_a:
                self.current_pos[0] = pos_id
                return pos_id
        self.current_pos[0] = len(self.ids) - 1
        return self.ids[-1]

    def intersection(self, b) -> array:
        b.reset()
        result = array('i')
        for doc_id_a in self.ids:
            doc_id_b = b.search(doc_id_a)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
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
        self.current_pos = [0] * (len(self.skip_lists) + 1)
        self.last_id = [-1] * (len(self.skip_lists) + 1)
