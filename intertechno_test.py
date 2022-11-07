#!/bin/python
import unittest
import intertechno
import queue

class MyTest( unittest.TestCase):
    def setUp(self):
        q = queue.Queue
        self.a = intertechno.Switch( '/IT/Switch11', '5A9A6A5A55555056', 'cul', q)
        self.a.set('ON')
        self.b = intertechno.Switch( '/IT/Switch1', '151550', 'cul', q)
        self.b.set('ON')
    
    def test_it_encoding_v1(self):
        self.assertEqual( self.b._encode(), b'is0FFF0FFFFFFF\n')

    def test_it_encoding_v3(self):
        self.assertEqual( self.a._encode(), b'is00111011011100110000000000010001\n')

if __name__ == '__main__':
    unittest.main()

