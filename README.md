# pysearchlite

Lightweight Text Search Engine written in Python

## Usage

### Corpus

Prepare a JSON file which contains lines of "id" and "text".

For example, [stn/search-backend-game](https://github.com/stn/search-benchmark-game)
has made such corpus. You can use it.

```shell
$ git clone https://github.com/stn/search-benchmark-game.git 
$ cd search-benchmark-game
$ make corpus
```

This will result in a corpus file `corpus.json`, which is about 8GB.
The corpus has more than 5 million documents,
but it is too large for our development,
so we will extract only the first some lines.

```shell
$ head -n 100 corpus.json > corpus100.json
```

### How to run

To run a sample script,
```shell
$ python -m pysearchlite.commands.main < corpus100.json
```

To run search-backend-game,
```shell
# Go to the search-benchmark-game dir.
# assume it's next of this repo.
$ cd ../search-benchmark-game
$ head -n 10000 corpus.json > corpus10k.json
$ make CORPUS=`pwd`/corpus10k.json index
$ make bench
$ make serve
```
