import json
import sys

import search_engine as se


INDEX_DIR = 'idx'


def index_file(docs_dir: str):
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        text = ' '.join(se.normalized_tokens(f.read()))
        se.index(filename, text)


def main():
    # Index
    for line in sys.stdin:
        d = json.loads(line)
        se.index(d['id'], d['text'])
    se.save_index(INDEX_DIR)
    se.restore_index(INDEX_DIR)
    # Search
    print(se.search('the'))
    print(se.search('los angeles'))
    print(se.search('the national football league'))


if __name__ == '__main__':
    main()
