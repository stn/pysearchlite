from .search_engine import (
    clear_index,
    count,
    index,
    init,
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
    MemoryInvertedIndex,
)

VERSION = '0.4.6'
