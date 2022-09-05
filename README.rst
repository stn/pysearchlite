pysearchlite
============

.. |Python package| image:: https://github.com/stn/pysearchlite/actions/workflows/python-package.yml/badge.svg?branch=main
   :target: https://github.com/stn/pysearchlite/actions/workflows/python-package.yml

Lightweight Text Search Engine written in Python

Usage
-----

Prepare a JSON file which contains lines of "id" and "text".

For example, `stn/search-backend-game <https://github.com/stn/search-benchmark-game>`_
has made such corpus. You can use it.

.. code:: console

   $ git clone https://github.com/stn/search-benchmark-game.git
   $ cd search-benchmark-game
   $ make corpus

This will result in a corpus file `corpus.json`, which is about 8GB.
The corpus has more than 5 million documents,
but it is too large for our development,
so we will extract only the first some lines.

.. code:: console

   $ head -n 100 corpus.json > corpus100.json

How to run
----------

To run a sample script,

.. code:: console

   $ python -m pysearchlite.commands.main < corpus100.json

To run search-backend-game,

.. code:: console

   # Go to the search-benchmark-game dir.
   # assume it's next of this repo.
   $ cd ../search-benchmark-game
   $ make index
   $ make bench
   $ make serve
