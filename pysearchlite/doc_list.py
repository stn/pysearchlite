import abc
import os

DOC_LIST_FILENAME = "doc_list"


class DocList(abc.ABC):

    def __init__(self, idx_dir: str):
        self.idx_dir = idx_dir

    @abc.abstractmethod
    def add(self, name: str) -> int:
        pass

    @abc.abstractmethod
    def get(self, idx: int) -> str:
        pass

    @abc.abstractmethod
    def save(self):
        pass

    @abc.abstractmethod
    def restore(self):
        pass

    @abc.abstractmethod
    def clear(self):
        pass

    def get_doc_filename(self):
        return os.path.join(self.idx_dir, DOC_LIST_FILENAME)


class MemoryDocList(DocList):

    def __init__(self, idx_dir: str):
        super().__init__(idx_dir)
        self.doc_list: list[str] = []

    def add(self, name: str) -> int:
        idx = len(self.doc_list)
        self.doc_list.append(name)
        return idx

    def get(self, idx: int) -> str:
        return self.doc_list[idx]

    def save(self):
        with open(self.get_doc_filename(), 'w', encoding='utf-8') as doc_f:
            for name in self.doc_list:
                doc_f.write(name)
                doc_f.write('\n')

    def restore(self):
        self.doc_list = []
        with open(self.get_doc_filename(), 'r', encoding='utf-8') as doc_f:
            for line in doc_f:
                self.doc_list.append(line[:-1])

    def clear(self):
        self.doc_list = []
