import json
import os
import sys

import pysearchlite as psl


def main(idx_dir):
    os.makedirs(idx_dir, exist_ok=True)
    for line in sys.stdin:
        d = json.loads(line)
        psl.index(d['id'], d['text'])
    psl.save_index(idx_dir)


if __name__ == '__main__':
    main(sys.argv[1])
