from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
import os
import io
import unittest
import avb

import avb.utils
import glob

def iter_chunks(chunk_type):
    chunk_dir = os.path.join(os.path.dirname(__file__), 'chunks', chunk_type, '*.chunk')

    for item in glob.glob(chunk_dir):
        yield item

class MockFile(object):
    def __init__(self, f):
        self.f = f
        self.check_refs = False

def decode_chunk(path):

    with io.open(path, 'rb') as f:
        m = MockFile(f)
        chunk = avb.file.read_chunk(m, f)
        obj_class = avb.utils.AVBClaseID_dict.get(chunk.class_id, None)
        assert obj_class
        try:
            object_instance = obj_class(m)
            object_instance.read(io.BytesIO(chunk.read()))
        except:
            print(path)
            print(chunk.class_id)
            print(chunk.hex())
            raise

class TestChuckDB(unittest.TestCase):


    def test_cdci_chunks(self):
        for chunk_path in iter_chunks("CDCI"):
            decode_chunk(chunk_path)

    def test_rgba_chunks(self):
        for chunk_path in iter_chunks("RGBA"):
            decode_chunk(chunk_path)

    def test_rset_chunks(self):
        for chunk_path in iter_chunks("RSET"):
            decode_chunk(chunk_path)

    def test_rept_chunks(self):
        for chunk_path in iter_chunks("REPT"):
            decode_chunk(chunk_path)

    def test_pvol_chunks(self):
        for chunk_path in iter_chunks("PVOL"):
            decode_chunk(chunk_path)

    def test_slct_chunks(self):
        for chunk_path in iter_chunks("SLCT"):
            decode_chunk(chunk_path)


if __name__ == "__main__":
    unittest.main()