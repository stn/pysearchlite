import abc
import os

DOC_LIST_FILENAME = "doc_list"


class DocList(abc.ABC):

    @abc.abstractmethod
    def add(self, name: str) -> int:
        pass

    @abc.abstractmethod
    def get(self, idx: int) -> str:
        pass

    @abc.abstractmethod
    def save(self, idx_dir: str):
        pass

    @abc.abstractmethod
    def restore(self, idx_dir: str):
        pass

    @abc.abstractmethod
    def clear(self):
        pass


class MemoryDocList(DocList):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir
        self.doc_list: list[str] = list()

    def add(self, name: str) -> int:
        idx = len(self.doc_list)
        self.doc_list.append(name)
        return idx

    def get(self, idx: int) -> str:
        return self.doc_list[idx]

    def save(self):
        with open(os.path.join(self.idx_dir, DOC_LIST_FILENAME), 'w', encoding='utf-8') as f:
            for name in self.doc_list:
                f.write(name)
                f.write('\n')

    def restore(self):
        self.doc_list = list()
        with open(os.path.join(self.idx_dir, DOC_LIST_FILENAME), 'r', encoding='utf-8') as f:
            for line in f:
                self.doc_list.append(line[:-1])

    def clear(self):
        self.doc_list = list()
