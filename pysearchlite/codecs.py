import mmap
import sys

TOKEN_LEN_BYTES = 2
DOCID_BYTES = 4
DOCID_LEN_BYTES = 4

SKIP_LIST_BLOCK_INDEX_BYTES = 4


BYTEORDER = "big"
B_INT32_0 = b"\x00\x00\x00\x00"

BLOCK_TYPE_DOC_ID = b"\x01"
BLOCK_TYPE_DOC_IDS_LIST = b"\x02"
BLOCK_TYPE_SKIP_LIST = b"\x03"


def write_token(f, token):
    encoded_token = token.encode('utf-8')
    # TODO: check overflow
    f.write(len(encoded_token).to_bytes(TOKEN_LEN_BYTES, BYTEORDER))
    f.write(encoded_token)


def read_token(f):
    token_bytes = f.read(TOKEN_LEN_BYTES)
    if not token_bytes:
        return ""
    token_len = int.from_bytes(token_bytes, BYTEORDER)
    return f.read(token_len).decode('utf-8')


def write_doc_ids(f, doc_ids):
    f.write(len(doc_ids).to_bytes(DOCID_LEN_BYTES, BYTEORDER))
    for doc_id in doc_ids:
        f.write(doc_id.to_bytes(DOCID_BYTES, BYTEORDER))


def read_doc_ids(f):
    doc_ids_len = int.from_bytes(f.read(DOCID_LEN_BYTES), BYTEORDER)
    doc_ids = []
    for _ in range(doc_ids_len):
        doc_ids.append(int.from_bytes(f.read(DOCID_BYTES), BYTEORDER))
    return doc_ids


def copy_ids(dst, src):
    docid_len_bytes = src.read(DOCID_LEN_BYTES)
    doc_ids_len = int.from_bytes(docid_len_bytes, BYTEORDER)
    dst.write(docid_len_bytes)
    doc_ids_bytes = src.read(doc_ids_len * DOCID_BYTES)
    dst.write(doc_ids_bytes)


def merge_ids(dst, src1, src2):
    doc_ids_len1 = int.from_bytes(src1.read(DOCID_LEN_BYTES), BYTEORDER)
    doc_ids_len2 = int.from_bytes(src2.read(DOCID_LEN_BYTES), BYTEORDER)
    dst.write((doc_ids_len1 + doc_ids_len2).to_bytes(DOCID_LEN_BYTES, BYTEORDER))
    doc_ids_bytes = src1.read(doc_ids_len1 * DOCID_BYTES)
    dst.write(doc_ids_bytes)
    doc_ids_bytes = src2.read(doc_ids_len2 * DOCID_BYTES)
    dst.write(doc_ids_bytes)


def write_block_skip_list(skip_list, file):
    file.write(BLOCK_TYPE_SKIP_LIST)
    file.write(skip_list.freq.to_bytes(DOCID_LEN_BYTES, sys.byteorder))
    file.write(skip_list.p.to_bytes(1, sys.byteorder))
    file.write(skip_list.max_level.to_bytes(1, sys.byteorder))
    file.write(len(skip_list.blocks).to_bytes(SKIP_LIST_BLOCK_INDEX_BYTES, sys.byteorder))
    block_size = (skip_list.p * 2 + 1) * DOCID_BYTES
    for i, block in enumerate(skip_list.blocks):
        b = skip_list.next_block_idx[i].to_bytes(DOCID_BYTES, sys.byteorder)
        b += b''.join([doc_id.to_bytes(DOCID_BYTES, BYTEORDER) for doc_id in block])
        if len(b) < block_size:
            b = b.ljust(block_size, b'\x00')
        file.write(b)


def write_doc_ids_list(doc_ids, file):
    file.write(BLOCK_TYPE_DOC_IDS_LIST)
    file.write(len(doc_ids.ids).to_bytes(DOCID_LEN_BYTES, sys.byteorder))
    for doc_id in doc_ids.ids:
        file.write(doc_id.to_bytes(DOCID_BYTES, BYTEORDER))


def read_doc_ids_list(mem, pos, freq):
    ids = []
    for _ in range(freq):
        ids.append(mem[pos:pos + DOCID_BYTES])
        pos += DOCID_BYTES
    return ids


def write_single_doc_id(doc_id, file):
    file.write(BLOCK_TYPE_DOC_ID)
    file.write(doc_id.doc_id.to_bytes(DOCID_BYTES, BYTEORDER))
