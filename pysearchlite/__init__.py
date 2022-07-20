from .search_engine import (
    clear_index,
    index,
    restore_index,
    save_index,
    search,
)
from .tokenize import normalized_tokens
from .doc_list import (
    DocList,
    MemoryDocList,
)
from .inverted_index import (
    InvertedIndex,
    AsciiFileInvertedIndex,
    MemoryInvertedIndex,
    SortBasedInvertedIndex,
)

VERSION = '0.3.3'
