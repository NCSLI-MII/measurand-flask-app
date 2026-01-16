#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import unittest

from miiflask.flask.app import app


class TestAppCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
    
    def test_home_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        print(response.json)
    
    def tearDown(self):
        self.app_context.pop()
