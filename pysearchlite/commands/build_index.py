import json
import os
import sys

import pysearchlite as psl


def main(idx_dir):
    psl.init(idx_dir)
    for line in sys.stdin:
        d = json.loads(line)
        psl.index(d['id'], d['text'])
    psl.save_index()


if __name__ == '__main__':
    main(sys.argv[1])
