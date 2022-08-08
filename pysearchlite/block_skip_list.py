import math
import os
from array import array


SKIPLIST_P = int(os.environ.get('PYSEARCHLITE_SKIPLIST_P', '8'))
SKIPLIST_MAX_LEVEL = int(os.environ.get('PYSEARCHLITE_SKIPLIST_MAX_LEVEL', '10'))


class BlockSkipList(object):

    def __init__(self):
        self.ids = None
        self.p = SKIPLIST_P
        self.skip_lists = None
        self.current_pos = None
        self.last_id = None

    @staticmethod
    def from_list(ids: list[int], p=SKIPLIST_P, max_level=SKIPLIST_MAX_LEVEL):
        if len(ids) == 1:
            return SingleDocId(ids[0])
        elif len(ids) <= p:
            return DocIdList(ids)

        max_height = min(math.log(max(len(ids) - 1, 1), p), max_level)

        skip_lists = [[]]
        for i in range(1, len(ids)):
            level = 1
            m = p
            while (i % m) == 0 and level <= max_height:
                if len(skip_lists) <= level:
                    skip_lists.append([ids[0]])
                skip_lists[level].append(ids[i])
                level += 1
                m *= p
        s = BlockSkipList()
        s.ids = array('i', ids)
        s.p = p
        s.skip_lists = [array('i', sl) for sl in skip_lists]
        return s

    def get_ids(self) -> list[int]:
        return self.ids.tolist()

    def search(self, doc_id_a: int):
        if len(self.skip_lists) == 1:
            # no skip list
            for i in range(self.current_pos[0], len(self.ids)):
                if self.ids[i] >= doc_id_a:
                    self.current_pos[0] = i
                    return self.ids[i]
            return self.ids[-1]

        # Check the start position.
        for level in range(0, len(self.skip_lists)):
            if doc_id_a <= self.last_id[level]:
                break
        pos = self.current_pos[level]
        if level > 0:
            skip_list = self.skip_lists[level]
            # When the first item is greater than the given doc id.
            if skip_list[pos] >= doc_id_a:
                return skip_list[pos]

        # skip list
        while level > 0:
            while True:
                pos_id = skip_list[pos]
                if pos_id < doc_id_a:
                    next_pos = pos + 1
                    if next_pos >= len(skip_list):
                        self.current_pos[level] = pos
                        self.last_id[level] = pos_id
                        break
                    pos = next_pos
                elif pos_id > doc_id_a:
                    pos -= 1
                    self.current_pos[level] = pos
                    self.last_id[level] = pos_id
                    break
                else:  # pos_id == doc_id_a:
                    self.current_pos[level] = pos
                    self.last_id[level] = pos_id
                    return pos_id
            pos = pos * self.p
            level -= 1
            skip_list = self.skip_lists[level]

        # ids
        for i in range(pos, len(self.ids)):
            pos_id = self.ids[i]
            if pos_id >= doc_id_a:
                self.current_pos[0] = i
                self.last_id[0] = pos_id
                return pos_id
        self.current_pos[0] = len(self.ids) - 1
        self.last_id[0] = self.ids[-1]
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
        self.current_pos = [0] * len(self.skip_lists)
        self.last_id = [-1] * len(self.skip_lists)


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
