import math
import os
from array import array


SKIPLIST_P = int(os.environ.get('PYSEARCHLITE_SKIPLIST_P', '4'))
OFFSET = int(os.environ.get('PYSEARCHLITE_SKIPLIST_OFFSET', '2'))


class BlockSkipList(object):

    def __init__(self):
        self.p = SKIPLIST_P
        self.ids = None
        self.skip_lists = None

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

    def search(self, doc_id_a: int, pos_b: int = 0):
        doc_id_b = -1
        if len(self.skip_lists) == 0:
            # no skip list
            for i in range(pos_b, len(self.ids)):
                if self.ids[i] >= doc_id_a:
                    return self.ids[i], i
            return self.ids[-1], len(self.ids)

        # top level
        level = len(self.skip_lists) - 1
        skip_list = self.skip_lists[level]
        if skip_list[pos_b] >= doc_id_a:
            return skip_list[pos_b], pos_b
        next_pos = pos_b + 1
        while next_pos < len(skip_list):
            if skip_list[next_pos] < doc_id_a:
                pos_b = next_pos
                next_pos += 1
            elif skip_list[next_pos] > doc_id_a:
                break
            else:  # ==
                return doc_id_a, pos_b

        # mid level
        level -= 1
        pos = pos_b
        while level >= 0:
            pos = pos * self.p
            skip_list = self.skip_lists[level]
            next_pos = pos + 1
            while next_pos < len(skip_list):
                if skip_list[next_pos] < doc_id_a:
                    pos = next_pos
                    next_pos += 1
                elif skip_list[next_pos] > doc_id_a:
                    break
                else:
                    return doc_id_a, pos_b
            level -= 1

        # ids
        pos = pos * self.p
        for i in range(pos, len(self.ids)):
            doc_id_b = self.ids[i]
            if doc_id_b >= doc_id_a:
                return doc_id_b, pos_b
        return doc_id_b, pos_b

    def intersection(self, b) -> array:
        result = array('i')
        pos_b = 0
        for doc_id_a in self.ids:
            doc_id_b, pos_b = b.search(doc_id_a, pos_b)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
        return result

    def intersection_with_doc_ids(self, a: array) -> array:
        result = array('i')
        pos_b = 0
        for doc_id_a in a:
            doc_id_b, pos_b = self.search(doc_id_a, pos_b)
            if doc_id_b == doc_id_a:
                result.append(doc_id_a)
        return result
