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
from .inverted_index import InvertedIndex
from .memory_inverted_index import MemoryInvertedIndex
from .spim_inveted_index import SinglePassInMemoryInvertedIndex


VERSION = '0.4.9'
