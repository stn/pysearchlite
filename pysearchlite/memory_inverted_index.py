from .inverted_index import InvertedIndex


class MemoryInvertedIndex(InvertedIndex):

    def __init__(self, idx_dir: str):
        super().__init__(idx_dir)
        self.data: dict[str, list[int]] = dict()

    def add(self, idx: int, tokens: list[str]):
        for token in set(tokens):
            if token in self.data:
                self.data[token].append(idx)
            else:
                self.data[token] = [idx]

    def get(self, token: str) -> list[int]:
        ids = self.data.get(token, [])
        return ids

    def search_and(self, tokens: list[str]) -> list[int]:
        raise NotImplementedError()

    def count_and(self, tokens: list[str]) -> int:
        raise NotImplementedError()

    def save(self):
        with open(self.get_inverted_index_filename(), 'w', encoding='utf-8') as f:
            for token, pos in self.data.items():
                f.write(token)
                f.write('\t')
                f.write(','.join(map(str, pos)))
                f.write('\n')

    def restore(self):
        self.data = dict()
        with open(self.get_inverted_index_filename(), 'r', encoding='utf-8') as f:
            for line in f:
                key_value = line[:-1].split('\t', maxsplit=1)
                key = key_value[0]
                pos = list(map(int, key_value[1].split(',')))
                self.data[key] = pos

    def clear(self):
        self.data = dict()
