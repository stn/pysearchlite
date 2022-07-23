import json
import sys

import pysearchlite as psl


def main():
    psl.init('idx')
    # Index
    for line in sys.stdin:
        d = json.loads(line)
        psl.index(d['id'], d['text'])
    psl.save_index()
    psl.clear_index()
    psl.restore_index()
    # Search
    print(psl.search('the'))
    print(psl.search('los angeles'))
    print(psl.search('the national football league'))


if __name__ == '__main__':
    main()
