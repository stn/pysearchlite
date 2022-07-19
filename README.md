# pysearchlite

Lightweight Text Search Engine written in Python

## Usage

### Corpus

Prepare a JSON file which contains lines of "id" and "text".

For example, [quickwit-oss/search-backend-game](https://github.com/quickwit-oss/search-benchmark-game)
has made such corpus. You can use it.

```shell
$ git clone https://github.com/quickwit-oss/search-benchmark-game.git 
$ cd search-benchmark-game
$ make corpus
```

This will result in a corpus file `corpus.json`, which is about 8GB.
The corpus has more than 5 million documents,
but it is too large for our development,
so we will extract only the first some lines.

```shell
$ head -n 1000 corpus.json > corpus1k.json
```

### How to run

To run a sample script
```shell
$ python -m pysearchlite.commands.main.py < corpus1k.json
```
