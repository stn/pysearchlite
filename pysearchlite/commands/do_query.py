import sys

import pysearchlite as psl


def main(idx_dir):
    psl.init(idx_dir)
    psl.restore_index()
    for line in sys.stdin:
        command_query = line.split('\t')
        command = command_query[0]
        query = command_query[1]
        if command == 'COUNT':
            count = psl.count(query)
        elif command == 'TOP_10':
            psl.search(query)
            count = 1
        elif command == 'TOP_10_COUNT':
            count = len(psl.search(query))
        else:
            sys.stderr.write("UNSUPPORTED\n")
            count = 0
        sys.stdout.write(str(count) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main(sys.argv[1])
