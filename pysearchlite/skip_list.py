from array import array
import random


SKIP_LIST_P = 2


class SkipList(object):

    def __init__(self):
        self.data = None

    @staticmethod
    def from_list(ids: list[int], p=SKIP_LIST_P):
        last_pointer = []
        skip_list = [array('i', [ids[0]])]
        for i in range(1, len(ids)):
            node = [ids[i]]
            level = 0
            while random.random() < (1.0 / p):
                node.append(-1)
                if len(last_pointer) > level:
                    skip_list[last_pointer[level]][level + 1] = i
                    last_pointer[level] = i
                else:
                    skip_list[0].append(i)
                    last_pointer.append(i)
                    break
                level += 1
            skip_list.append(array('i', node))
        s = SkipList()
        s.data = skip_list
        return s

    def get_ids(self) -> list[int]:
        return [node[0] for node in self.data]

    def search(self, doc_id_a: int, pos_b: int = 0):
        doc_id_b = -1
        if len(self.data[0]) == 1:
            # no skip list
            for i in range(pos_b, len(self.data)):
                doc_id_b = self.data[i][0]
                if doc_id_b >= doc_id_a:
                    return doc_id_b, i
            return doc_id_b, len(self.data)

        pos_b = [pos_b] * len(self.data[0])
        level = len(pos_b) - 1
        while level > 0:
            pos = pos_b[level]
            next_pos = self.data[pos][level]
            if next_pos >= 0 and self.data[next_pos][0] < doc_id_a:
                pos_b[level] = next_pos
            else:
                level -= 1
                pos_b[level] = pos
        for i in range(pos, len(self.data)):
            doc_id_b = self.data[i][0]
            if doc_id_b >= doc_id_a:
                return doc_id_b, pos_b[-1]
        return doc_id_b, pos_b[-1]

    def intersection(self, b) -> array:
        result = array('i')
        pos_b = 0
        for node in self.data:
            doc_id_a = node[0]
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
