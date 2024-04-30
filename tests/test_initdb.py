#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2024 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rdflib import plugin, Graph, Literal, URIRef
from rdflib.store import Store
from rdflib_sqlalchemy.store import SQLAlchemy
from rdflib.tools.rdf2dot import rdf2dot
import io
import pydotplus

from miiflask.flask.db import bind_engine
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper
from miiflask.flask.model import Scale, Unit

from tests.sqlalchemy_data_model_visualizer import generate_data_model_diagram

class InitializeDbTestCase(unittest.TestCase):
    ident = URIRef("rdflib_test")
    uri = Literal("sqlite://")

    tarek = URIRef(u"tarek")
    likes = URIRef(u"likes")
    pizza = URIRef(u"pizza")
    triples = []

    def setUp(self):
        self.engine = create_engine(self.uri)
        bind_engine(self.engine)
        #self.store = plugin.get("SQLAlchemy", Store)(identifier=self.ident)
        self.store = SQLAlchemy(identifier=self.ident, engine=self.engine)
        self.graph = Graph(self.store, identifier=self.ident)
        

    def tearDown(self):
        pass

    def test1_initdb(self):
        parms = {
                "measurands": "resources/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
                "mlayer": "resources/m-layer",
                "kcdb": "resources/kcdb",
                "api_mlayer": "https://dr49upesmsuw0.cloudfront.net",
                "use_api": False,
                "use_cmc_api": False,
                "update_resources": False
            }
        with Session(self.engine) as session:
            mapper = MlayerMapper(session, parms)
            mapper.getCollections()
            mapper.getScaleAspectAssociations()

            miimapper = TaxonomyMapper(session, parms)
            miimapper.extractTaxonomy()
            miimapper.loadTaxonomy()

            kcdbmapper = KcdbMapper(session, parms)
            kcdbmapper.loadServices()
            
            scales = session.query(Scale).all()
            for scale in scales:
                uriref_scale = URIRef(str(scale.id))
                uriref_unit = URIRef(str(scale.unit.id))
                uriref_relation = URIRef(u"expressedOn")
                self.triples.append((uriref_scale, uriref_relation, uriref_unit))
            print(len(self.triples))

    def test2_graph(self):
        tarek = self.tarek
        likes = self.likes
        pizza = self.pizza
        self.graph.open(self.uri, create=True)
        self.graph.add((tarek, likes, pizza))
        self.graph.commit()
        print(self.graph)
        #print(self.graph.store)
        print(self.graph.triples((self.tarek, None, None)))
        #print(self.graph.serialize(format='json-ld', indent=4))
        self.graph.close()

    def test3_graph_mlayer(self):
        _triples = self.triples
        print(len(_triples))
        for triple in _triples: 
            self.graph.open(self.uri, create=True)
            self.graph.add(triple)
         
        self.graph.commit()
        
        print(len(list(self.graph.triples((None, URIRef(u"expressedOn"), None)))))
        print(self.graph.triples((URIRef(str("SC1")),None,None)))
        self.graph.close()
        graph_scale = Graph(self.store, identifier=URIRef("rdf_scale"))
        graph_scale.open(self.uri, create=True)
        graph_scale.add(_triples[0])
        graph_scale.commit()

        stream = io.StringIO()
        rdf2dot =(graph_scale, stream)
        #print(stream.getvalue())
        #print(graph_scale.serialize(format='json-ld', indent=4))
        #dg = pydotplus.graph_from_dot_data(stream.getvalue())
        #dg.write_png("graph.png")
        
    def test4_rdf_serialize(self):
         
         testrdf = '''
         @prefix dc: <http://purl.org.dc/terms/> .
         <http://example.org/about>
             dc:title "Someone's homepage"@en .
         '''
         graph_test = Graph(self.store, identifier=URIRef("rdf_test"))
         graph_test.open(self.uri, create=True)
         #graph_test.parse(data=testrdf,format='n3')
         #print(graph_test.serialize(format='json-ld', indent=4))
     
    def test_visual(self):
        generate_data_model_diagram([Scale, Unit], "model.png")


if __name__ == '__main__':
    unittest.main()
