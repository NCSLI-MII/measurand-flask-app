#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
from flask import (render_template,
                   redirect,
                   url_for,
                   Markup)
from flask_admin.contrib.sqla import ModelView

from miiflask.flask.model import (
    Measurand,
    Taxon,
    Aspect,
    Scale,
    Unit,
    Prefix,
    Dimension,
    Conversion,
    Cast,
    Transform,
    System,
    Parameter,
    KcdbCmc
)
from miiflask.flask.model import AspectSchema, MeasurandSchema

from miiflask.flask.app import app
from miiflask.flask.app import db
from miiflask.mappers.taxonomy_mapper import dicttoxml_taxonomy, getTaxonDict
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper
from miiflask.utils.model_visualizer import generate_data_model_diagram, visualize_scale 

from marshmallow import pprint as mpprint
import json
import graphviz
import base64

qk_schema = AspectSchema()
m_schema = MeasurandSchema()


def _link_formatter(view, context, model, name):
    field = getattr(model, name)
    if field is None:
        return u""
    url = url_for('{}.details_view'.format(name), id=field.id)
    return Markup('<a href="{}">{}</a>'.format(url, field))


def _id_formatter(view, context, model, name):
    url = url_for(f'{model.__tablename__}.details_view', id=model.id)
    return Markup(f"<a href={url}>{model.id}</a>") if model.id else u""


class MyModelView(ModelView):
    def __init__(self, model, *args, **kwargs):
        self.form_columns = [c.key for c in model.__table__.columns]
        super(MyModelView, self).__init__(model, *args, **kwargs)

    can_view_details = True
    column_display_pk = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter}


class KcdbServiceView(MyModelView):
    column_searchable_list = ['area_id']
    page_size = 100


class CMCView(MyModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_searchable_list = ['area.label', 'quantity.value', 'kcdbCode']
    column_filters = ('area', 'service')
    column_list = ('id',
                   'kcdbCode',
                   'area',
                   'branch',
                   'service',
                   'subservice',
                   'individualservice',
                   'quantity',
                   'measurands',
                   'instrument',
                   'instrumentmethod',
                   )
    column_details_list = ('id',
                           'kcdbCode',
                           'area',
                           'branch',
                           'service',
                           'subservice',
                           'individualservice',
                           'quantity',
                           'measurands',
                           'instrument',
                           'instrumentmethod',
                           'baseUnit',
                           'uncertainityBaseUnit',
                           'parameters',
                           'comments'
                           )


class TaxonView(ModelView):
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    form_columns = ['id',
                    'measurands',
                    'aspect',
                    'discipline',
                    'subtaxons',
                    'supertaxon',
                    'deprecated',
                    'name',
                    'quantitykind',
                    'processtype'] 
    column_formatters = {'id': _id_formatter}
    column_list = ("id", "name", "deprecated") 
    column_details_list = ("id",
                           "name",
                           "deprecated",
                           )


class MeasurandView(ModelView):
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter,
                         'taxon': _link_formatter}
    column_list = ("id", "name", "quantitykind", "parameters")
    inline_models = (Parameter,)
    column_details_list = ("id",
                           "name",
                           "taxon",
                           "aspect",
                           "quantitykind",
                           "parameters",
                           "definition"
                           )


class DimensionView(MyModelView):

    def _link_system_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('system.details_view', id=model.formal_system.id)
        return Markup('<a href="{}">{}</a>'.format(url, field))

    def _link_scale_formatter(view, context, model, name):
        urls = []
        for s in model.systematic_scales:
            url = url_for('scale.details_view', id=s.id)
            urls.append('<a href="{}">{}</a>'.format(url, s.id))
        return Markup((',').join(urls))

    def _exponents_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        exponents = json.loads(field)
        dim = ['M', 'L', 'T', 'I', '&#920', 'N', 'J']
        dimQ = ''.join([m+'<sup>'+str(n)+'</sup>' for m, n in zip(dim, exponents)])
        return Markup(dimQ)

    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_list = ("id",
                   "formal_system",
                   "exponents")
    column_details_list = ("id",
                           "formal_system",
                           "systematic_scales",
                           "exponents")
    column_formatters = {"id": _id_formatter,
                         "formal_system": _link_system_formatter,
                         "systematic_scales": _link_scale_formatter,
                         "exponents": _exponents_formatter}


class ScaleView(ModelView):

    def _root_link_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('scale.details_view', id=field)
        return Markup('<a href="{}">{}</a>'.format(url, field))

    def _link_dim_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('dimension.details_view', id=model.system_dimensions.id)
        return Markup('<a href="{}">{}</a>'
                      .format(url, model.system_dimensions.id))

    def _cnv_link_formatter(view, context, model, name):
        urls = []
        for s in model.conversions:
            id_ = '{},{},{}'.format(s.src_scale_id,
                                    s.dst_scale_id,
                                    s.aspect_id)
            url = url_for('conversion.details_view', id=id_)
            urls.append('<a href="{}">{}</a>'.format(url,
                                                     id_.replace(',', '.')))
        return Markup((',').join(urls))

    def _cast_link_formatter(view, context, model, name):
        urls = []
        for s in model.casts:
            id_ = '{},{},{},{}'.format(s.src_scale_id,
                                       s.src_aspect_id,
                                       s.dst_scale_id,
                                       s.dst_aspect_id)
            url = url_for('cast.details_view', id=id_)
            urls.append('<a href="{}">{}</a>'.format(url,
                                                     id_.replace(',', '.')))
        return Markup((',').join(urls))

    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {'unit': _link_formatter,
                         'prefix': _link_formatter,
                         'root_scale_id': _root_link_formatter,
                         'conversions': _cnv_link_formatter,
                         'casts': _cast_link_formatter,
                         'system_dimensions': _link_dim_formatter}
    column_list = ("id",
                   "ml_name",
                   "unit")
    column_details_list = ("id",
                           "ml_name",
                           'scale_type',
                           "unit",
                           'root_scale_id',
                           'prefix',
                           "conversions",
                           "casts",
                           "system_dimensions",
                           'is_systematic'
                           )


class CastConversionView(MyModelView):
    column_formatters = {'transform': _link_formatter}


class AspectView(MyModelView):

    def _scale_formatter(view, context, model, name):
        urls = []
        for s in model.scales:
            url = url_for('scale.details_view', id=s.id)
            urls.append('<a href="{}">{}</a>'.format(url, s.id))

        return Markup((',').join(urls))

    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter,
                         'scales': _scale_formatter}
    column_list = ("id",
                   "name",
                   "ml_name",
                   "scales")
    column_details_list = ("id",
                           "name",
                           "ml_name",
                           "scales",
                           "conversions"
                           )


@app.route("/")
def index():
    meta = db.session.info
    print(meta)
    measurands = Measurand.query.all()
    aspects = Aspect.query.all()
    scales = Scale.query.all()
    return render_template(
        "index.html",
        measurands=measurands,
        aspects=aspects,
        scales=scales,
    )


@app.route("/initialize")
def initialize():

    parms = {
            "measurands": "../../resources/measurand-taxonomy/MeasurandTaxonomyCatalog.xml",
            "mlayer": "../../resources/m-layer",
            "kcdb": "../../resources/kcdb",
            "api_mlayer": "https://dr49upesmsuw0.cloudfront.net",
            "use_api": False,
            "use_cmc_api": False,
            "update_resources": False
        }

    mapper = MlayerMapper(db.session, parms)
    mapper.getCollections()
    mapper.getScaleAspectAssociations()

    miimapper = TaxonomyMapper(db.session, parms)
    miimapper.extractTaxonomy()
    miimapper.loadTaxonomy()

    kcdbmapper = KcdbMapper(db.session, parms)
    kcdbmapper.loadServices()
    db.session.commit()
    return redirect(url_for('index'))


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
    a = Aspect.query.get_or_404(aspect_id)
    a_schema = qk_schema.dumps(a, indent=2)
    print(a.id)
    mpprint(a_schema)
    return render_template("aspect.html", aspect=a, response=a_schema)


@app.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
def scale(scale_id):
    print("Get Scale ", scale_id)
    s = Scale.query.get_or_404(scale_id)
    print(s.id)
    graph = visualize_scale(Scale, s)
    return render_template("scale.html", scale=s, graph=graph)


@app.route("/model/mii")
def modelMII():
    models = [Scale, Aspect, Conversion, Cast, Transform, Measurand, KcdbCmc]
    excludes = ['Prefix',
                'Unit',
                'Dimension',
                'Taxon',
                'Parameter',
                'ClassifierTag',
                'KcdbArea',
                'KcdbBranch',
                'KcdbService',
                'KcdbSubservice',
                'KcdbIndividualService',
                'KcdbQuantity',
                'KcdbParameter',
                'KcdbInstrument',
                'KcdbInstrumentMethod']
    graph = generate_data_model_diagram(models, excludes,show_attributes=False)
    return render_template("diagram.html", graph=graph)


@app.route("/model/mlayer/scale")
def modelMlayerScale():
    models = [Scale, Unit, Prefix, Dimension, System]
    excludes = ['Aspect', 'Conversion', 'Cast']
    graph = generate_data_model_diagram(models, excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/mlayer/conversion")
def modelMlayerConversion():
    models = [Conversion, Aspect, Scale, Transform]
    excludes = ['Prefix', 'Unit', 'Dimension', 'Cast']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/mlayer/cast")
def modelMlayerCast():
    models = [Cast, Aspect, Scale, Transform]
    excludes = ['Prefix', 'Unit', 'Dimension', 'Conversion']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/taxonomy/measurand")
def modelTaxonomyMeasurand():
    models = [Taxon, Measurand, Parameter, Aspect]
    excludes = ['Scale', 'KcdbCmc']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/kcdb")
def modelKcdb():
    models = [KcdbCmc, Measurand]
    excludes = ['Taxon', 'Aspect', 'Parameter', 'ClassifierTag']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)
