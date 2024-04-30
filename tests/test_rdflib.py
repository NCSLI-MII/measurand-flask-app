#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
import unittest
from rdflib import plugin, Graph, Literal, URIRef
from rdflib.store import Store

class SQLASQLiteGraphTestCase(unittest.TestCase):
    ident = URIRef("rdflib_test")
    uri = Literal("sqlite://")

    def setUp(self):
        self.graph = Graph("SQLAlchemy", identifier=self.ident)
        self.graph.open(self.uri, create=True)

    def tearDown(self):
        self.graph.destroy(self.uri)
        try:
            self.graph.close()
        except:
            pass

    def test01(self):
        self.assert_(self.graph is not None)
        print(self.graph)

    if __name__ == '__main__':
        unittest.main()
