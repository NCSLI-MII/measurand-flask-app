#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import os
os.environ["FLASK_CONFIG"] = "test"      # or however your app selects config
from miiflask.flask.app import create_app
import unittest
from miiflask.flask.config import TestingConfig


class TestAppCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestingConfig)

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_home_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


