import json
import os
import sys

import pysearchlite as psl


INDEX_DIR = 'idx'


def index_file(docs_dir: str):
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        text = ' '.join(psl.normalized_tokens(f.read()))
        psl.index(filename, text)


def main():
    # Index
    for line in sys.stdin:
        d = json.loads(line)
        psl.index(d['id'], d['text'])
    os.makedirs(INDEX_DIR, exist_ok=True)
    psl.save_index(INDEX_DIR)
    psl.restore_index(INDEX_DIR)
    # Search
    print(psl.search('the'))
    print(psl.search('los angeles'))
    print(psl.search('the national football league'))


if __name__ == '__main__':
    main()
