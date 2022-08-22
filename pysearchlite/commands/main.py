import json
import sys

import pysearchlite as psl


def main():
    psl.init('idx')
    # Index
    for line in sys.stdin:
        doc = json.loads(line)
        psl.index(doc['id'], doc['text'])
    psl.save_index()

    psl.init('idx')
    psl.restore_index()
    # Search
    print(psl.search('united states constitution'))
    print(psl.search('search'))
    print(psl.search('los angeles'))
    print(psl.search('the national football league'))
    print(psl.search('the book of life'))
    print(psl.search('care a lot'))
    print(psl.search('usb hub'))

    psl.close()


if __name__ == '__main__':
    main()
