#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
from flask import render_template, redirect, url_for, make_response, send_file, Markup
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.view import func

from io import StringIO, BytesIO
import csv
import pandas as pd

from itertools import groupby
from operator import attrgetter

from miiflask.flask.model import (
    Measurand,
    Aspect, 
    Scale,
    Domain,
    KcdbCmc, 
)
from miiflask.flask.model import AspectSchema, MeasurandSchema

from miiflask.flask.app import app
from miiflask.flask.app import db
from miiflask.mappers.taxonomy_mapper import dicttoxml_taxonomy, getTaxonDict

from marshmallow import pprint as mpprint

qk_schema = AspectSchema()
m_schema = MeasurandSchema()


class MyModelView(ModelView):
    def _id_formatter(view, context, model, name):
        _url = f'{view.url}/details/?id={model.id}'
        print(_url)
        return Markup(u"<a href='%s'>%s</a>" % (_url, model.id)
                ) if model.id else u""
    can_view_details = True
    column_display_pk = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter}


class CMCView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ("id", "tags")


class MeasurandView(ModelView):
    
    def _id_formatter(view, context, model, name):
        print(model.__dict__)
        return Markup(u"<a href='%s'>%s</a>" % (url_for('%s.details_view' % model.__tablename__, id=model.id), model.id)
                ) if model.id else u""
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter}
    column_list = ("id", "name", "quantitykind", "parameters")
    column_details_list = ("id", 
            "name", 
            "aspect",
            "quantitykind", 
            "parameters",
            "definition"
                           )
    




@app.route("/")
def index():
    measurands = Measurand.query.all()
    aspects = Aspect.query.all()
    scales = Scale.query.all()
    return render_template(
        "index.html",
        measurands=measurands,
        aspects=aspects,
        scales=scales,
    )

@app.route("/taxonomy/")
def taxonomy():
    measurand = Measurand()
    measurands = measurand.query.all()
    return render_template("taxonomy.html", measurands=measurands)

@app.route("/taxonomy/export")
def taxonomy_export():
    measurand = Measurand()
    measurands = measurand.query.all()
    taxons = []
    
    for obj in measurands:
        taxons.append(getTaxonDict(obj, m_schema))
    xml = dicttoxml_taxonomy(taxons)
    response = app.make_response(xml)
    response.mimetype = "text/xml"
    return response

@app.route("/measurand/<string:measurand_id>/", methods=["GET", "POST"])
def measurand(measurand_id):
    print("Get Meaurand ", measurand_id)
    m = Measurand.query.get_or_404(measurand_id)
    schema = m_schema.dumps(m, indent=2)
    print(m.id)
    mpprint(schema)
    return render_template("measurand.html", measurand=m, response=schema)


@app.route("/aspect/<string:aspect_id>/", methods=["GET", "POST"])
def aspect(aspect_id):
    print("Get Aspect ", aspect_id)
    a = QuantityKind.query.get_or_404(aspect_id)
    a_schema = qk_schema.dumps(a, indent=2)
    print(a.id)
    mpprint(a_schema)
    return render_template("aspect.html", aspect=a, response=a_schema)


@app.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
def scale(scale_id):
    print("Get Scale ", scale_id)
    s = Scale.query.get_or_404(scale_id)
    print(s.id)
    return render_template("scale.html", scale=s)


