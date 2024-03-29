import json
import sys

import pysearchlite as psl


def main(idx_dir):
    psl.init(idx_dir)
    for line in sys.stdin:
        doc = json.loads(line)
        psl.index(doc['id'], doc['text'])
    psl.save_index()


if __name__ == '__main__':
    main(sys.argv[1])
