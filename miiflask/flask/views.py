#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
import logging

from sqlalchemy.orm.base import instance_state
from flask import (render_template,
                   redirect,
                   request,
                   url_for,
                   flash
                   )

from flask_admin.contrib.sqla import ModelView
from flask_admin.model.filters import BaseFilter
from flask_admin.babel import gettext

from flask_admin.actions import action
from flask_admin import Admin, expose
from flask_admin.helpers import get_redirect_target

from wtforms import HiddenField, StringField, Form
from wtforms.validators import InputRequired

from markupsafe import Markup
from miiflask.flask.model import (
    Administrative,
    Measurand,
    MeasurandTaxon,
    Discipline,
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
    Reference,
    KcdbCmc,
    KcdbBranch,
    KcdbParameter,
    KcdbArea
)
from miiflask.flask.model import AspectSchema, MeasurandTaxonSchema, KcdbCmcSchema

from miiflask.flask.app import app
from miiflask.flask.app import db
#from miiflask.mappers.taxonomy_mapper import dicttoxml_taxonomy, getTaxonDict
from miiflask.mappers.mlayer_mapper import MlayerMapper
from miiflask.mappers.taxonomy_mapper_v2 import TaxonomyMapper
from miiflask.mappers.kcdb_mapper import KcdbMapper
from miiflask.utils.model_visualizer import (
    generate_data_model_diagram,
    visualize_model_instance
    )

import pprint as mpprint
import json
import graphviz
import base64

log = logging.getLogger("flask-admin.sqla")

qk_schema = AspectSchema()
m_schema = MeasurandTaxonSchema()
cmc_schema = KcdbCmcSchema()

def _link_formatter(view, context, model, name):
    field = getattr(model, name)
    if field is None:
        return u""
    url = url_for('{}.details_view'.format(name), id=field.id)
    return Markup('<a href="{}">{}</a>'.format(url, field))


def _id_formatter(view, context, model, name):
    url = url_for(f'{model.__tablename__}.details_view', id=model.id)
    return Markup(f"<a href={url}>{model.id}</a>") if model.id else u""




class MyBaseFilter(BaseFilter):
    def __init__(self, column, name, options=None, data_type=None):
        super(MyBaseFilter, self).__init__(name, options, data_type)
        self.column = column


class MyEqualFilter(MyBaseFilter):
    def apply(self, query, value, alias=None):
        return query.filter(self.column == value)

    def operation(self):
        return gettext('equals')

    # Possible to validate input values,
    # return 'False', filter is ignored

    def validate(self, value):
        return True
    
    # Clean values before accessing data access layer

    def clean(self, value):
        return value


class MyUniqueFilter(MyBaseFilter):
# TBD
    def apply(self, query, value, alias=None):
        return query.with_entities(self.column).distinct()

    def operation(self):
        return gettext('unique')

    # Possible to validate input values,
    # return 'False', filter is ignored

    def validate(self, value):
        return True
    
    # Clean values before accessing data access layer

    def clean(self, value):
        return value


class MyModelView(ModelView):
    def __init__(self, model, *args, **kwargs):
        self.form_columns = [c.key for c in model.__table__.columns]
        super(MyModelView, self).__init__(model, *args, **kwargs)
    page_size = 100
    can_view_details = True
    column_display_pk = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter}


class KcdbServiceView(MyModelView):
    column_searchable_list = ['area_id']
    page_size = 100


class KcdbBranchView(MyModelView):
    page_size = 100 

class ChangeForm(Form):
    ids = HiddenField()
    measurand = StringField(validators=[InputRequired()])

class CMCView(MyModelView):
    list_template = 'custom_list.html' 
    def _parameter_formatter(view, context, model, name):
        names = [p.name for p in model.parameters]
        return Markup((',<br/>').join(names))
    
    def _measurand_formatter(view, context, model, name):
        urls = []
        for p in model.measurands:
            url = url_for('measurandtaxon.details_view', id=p.id)
            urls.append('<a href="{}">{}</a>'.format(url, p.name))
        return Markup((', <br/>').join(urls))
    # Custom action to link CMCs to measurand
    # See Flask-admin actions
    # See example github.com/pjcunningham/flask-admin-modal

    @action('change_measurand', 'Measurand')
    def action_change_measurand(self, ids):
        url = get_redirect_target() or self.get_url('.index_view')
        return redirect(url, code=307)
    
    @expose('/', methods=['POST'])
    def index(self):
        if request.method == 'POST':
            url = get_redirect_target() or self.get_url('.index_view')
            ids = request.form.getlist('rowid')
            joined_ids = ','.join(ids)
            change_form = ChangeForm()
            change_form.ids.data = joined_ids
            self._template_args['url'] = url
            self._template_args['change_form'] = change_form
            self._template_args['change_modal'] = True
            return self.index_view()

    @expose('/update/', methods=['POST'])
    def update_view(self):
        if request.method == 'POST':
            url = get_redirect_target() or self.get_url('.index_view')
            change_form = ChangeForm(request.form)
            if change_form.validate():
                ids = change_form.ids.data.split(',')
                measurand = change_form.measurand.data
                #_update_mappings = [{'id': rowid, 'measurand_id': measurand} for rowid in ids]
                query = KcdbCmc.query.filter(KcdbCmc.id.in_(ids))
                m_query = MeasurandTaxon.query.filter(MeasurandTaxon.id == measurand).first()
                if m_query is None:
                    flash(f"Set measurand for {len(ids)} record{'s' if len(ids) > 1 else ''} to {measurand} failed. Cannot query {measurand}", category='info')
                    return redirect(url)
                for cmc in query.all():
                    cmc.measurands.append(m_query)

                #db.session.bulk_update_mappings(KcdbCmc, _update_mappings)
                db.session.commit()
                flash(f"Set measurand for {len(ids)} record{'s' if len(ids) > 1 else ''} to {measurand}.", category='info')
                return redirect(url)
            else:
                self._template_args['url'] = url
                self._template_args['change_form'] = change_form
                self._template_args['change_modal'] = True
                return self.index_view()

                
    page_size = 100
    column_display_pk = True
    column_hide_backrefs = False
    can_export = True
    column_searchable_list = ['area.label', 
                              'quantity.value', 
                              'kcdbCode']
    column_filters = ('area.label', 
                      'branch.value', 
                      'service.value',
                      'subservice.value',
                      'individualservice.value',
                      MyEqualFilter(KcdbCmc.kcdbCode, 'kcdbCode'))
    column_formatters = {'parameter_names': _parameter_formatter,
            'measurands': _measurand_formatter}
    column_labels = {'parameter_names': 'Parameters'}
    column_list = ('id',
                   'kcdbCode',
                   'quantity',
                   'measurands',
                   'area',
                   'branch',
                   'service',
                   'subservice',
                   'individualservice',
                   'instrument',
                   'instrumentmethod',
                   'baseUnit',
                   'uncertaintyBaseUnit',
                   'internationalStandard',
                   'comments',
                   'parameter_names'
                   )

    column_details_list = ('id',
                           'kcdbCode',
                           'quantity',
                           'measurands',
                           'area',
                           'branch',
                           'service',
                           'subservice',
                           'individualservice',
                           'instrument',
                           'instrumentmethod',
                           'baseUnit',
                           'uncertaintyBaseUnit',
                           'internationalStandard',
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
    
    def on_model_change(self, form, model, is_created):
        "Custom model change" 
        pass
        
    def create_model(self, form):
        """
            Create model from form.

            :param form:
                Form instance
        """
        try:
            model = self._manager.new_instance()
            # TODO: We need a better way to create model instances and stay compatible with
            # SQLAlchemy __init__() behavior
            state = instance_state(model)
            self._manager.dispatch.init(state, [], {})
            
            form.populate_obj(model)
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                log.exception('Failed to create record.')

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, True)

        return model
    
    def update_model(self, form, model):
        try:
            form.populate_obj(model)
            
            # At this point model has form values
            self._on_model_change(form, model, False)
            # or try to modify here
            self.session.commit()

        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to update record. %(error)s', error=str(ex)), 'error')
                log.exception('Failed to update record')
            self.session.rollback()

            return False
        else:
            # model committed to database
            self.after_model_change(form, model, False)
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {
            'id': _id_formatter,
            'taxon': _link_formatter,
            'aspect': _link_formatter,
            'scale': _link_formatter
            }
    column_list = (
            "id", 
            "name",
            "aspect", 
            "quantitykind", 
            "parameters"
            )
    inline_models = (Parameter,)
    column_details_list = (
           "id",
           "name",
           "taxon",
           "aspect",
           "quantitykind",
           "parameters",
           "definition",
           "result",
           )


class ParameterView(ModelView):
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_searchable_list = ['name']
    
    column_formatters = {
            'id': _id_formatter,
            'aspect': _link_formatter,
            'measurandtaxon': _link_formatter,
            }
    
    column_labels = {
            'aspect': 'Parameter aspect',
            'quantitykind': 'UOM Quantity',
            'measurandtaxon': 'Corresponding taxon'
            }

    column_list = (
            "id", 
            "name",
            "measurandtaxon",
            "aspect", 
            "definition"
            )

    column_details_list = (
           "id",
           "name",
           "aspect",
           "measurandtaxon",
           "definition",
           "quantitykind",
           )
    form_excluded_columns = ('quantitykind','measurandtaxon','measurand')


class MeasurandTaxonView(ModelView):
    
    def _parameter_formatter(view, context, model, name):
        urls = []
        for p in model.parameters:
            url = url_for('parameter.details_view', id=p.id)
            urls.append('<a href="{}">{}</a>'.format(url, p.name))
        return Markup((', <br/>').join(urls))
   
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_searchable_list = ['name']
    
    column_labels = {
            'parameter_names': 'Parameters',
            'result': 'Result name',
            'aspect': 'Result aspect',
            'quantitykind': 'UOM Quantity'
            }
    
    column_formatters = {
            'id': _id_formatter,
            'aspect': _link_formatter,
            'scale': _link_formatter,
            'parameter_names': _parameter_formatter,
            }
    column_list = (
            "id", 
            "name",
            "aspect", 
            "definition"
            )
    inline_models = [(Parameter, dict(form_excluded_columns=['quantitykind','measurandtaxon','measurand'])), Reference]
    column_details_list = (
           "id",
           "name",
           "aspect",
           "result",
           "definition",
           "quantitykind",
           "parameter_names",
           )
    form_columns = ['id',
                    'name',
                    'result',
                    'aspect',
                    'quantitykind',
                    'deprecated',
                    'replacement',
                    'definition',
                    #'processtype',
                    #'qualifier',
                    #'kcdbcmcs',
                    'parameters',
                    'external_references'] 


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
            id_ = '{}: {} &#8594 {}'.format(s.aspect.name,
                                    s.src_scale.ml_name,
                                    s.dst_scale.ml_name)
            url = url_for('conversion.details_view', id=id_)
            urls.append('<a href="{}">{}</a>'.format(url,
                                                     id_.replace(',', '.')))
        return Markup((', <br/>').join(urls))

    def _cast_link_formatter(view, context, model, name):
        urls = []
        for s in model.casts:
            id_ = '{}: {} &#8594 {}: {}'.format(s.src_aspect.name,
                                       s.src_scale.ml_name,
                                       s.dst_aspect.name,
                                       s.dst_scale.ml_name)
            url = url_for('cast.details_view', id=id_)
            urls.append('<a href="{}">{}</a>'.format(url,
                                                     id_.replace(',', '.')))
        return Markup((', <br/>').join(urls))
    
    column_searchable_list = ['ml_name']
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
    column_searchable_list = ['name']
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
    measurands = MeasurandTaxon.query.all()
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
            "update_resources": False,
            "kcdb_cmc_data": "kcdb_cmc_canada.json",
            "kcdb_cmc_api_countries": ["CA"],
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
    measurand = MeasurandTaxon()
    measurands = measurand.query.all()
    return render_template("taxonomy.html", measurands=measurands)


@app.route("/kcdbcmcs/")
def kcdbcmcs():
    cmc = KcdbCmc()
    cmcs = cmc.query.all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/export/json")
def kcdbcmcs_export_json():
    cmc = KcdbCmc()
    cmcs = cmc.query.all()
    schema = cmc_schema.dumps(cmcs, many=True, indent=4)
    response = app.make_response(schema)
    response.headers["Content-Disposition"] = "attachment; filename=export_cmcs.json"
    response.headers["Content-type"] = "text/json"
    return response 


@app.route("/kcdbcmcs/auv/")
def kcdbcmcs_auv():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'AUV')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/em/")
def kcdbcmcs_em():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'EM')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/l/")
def kcdbcmcs_l():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'L')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/m/")
def kcdbcmcs_m():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'M')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/pr/")
def kcdbcmcs_pr():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'PR')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/t/")
def kcdbcmcs_t():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'T')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmcs/tf/")
def kcdbcmcs_tf():
    cmcs = KcdbCmc.query.filter(KcdbCmc.area.has(KcdbArea.label == 'TF')).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@app.route("/kcdbcmc/<string:kcdbcmc_id>/export/json", methods=["GET", "POST"])
def kcdbcmc_export_json(kcdbcmc_id):
    # print("Get Meaurand ", measurand_id)
    cmc = KcdbCmc.query.get_or_404(kcdbcmc_id)
    schema = cmc_schema.dumps(cmc, indent=2)
    response = app.make_response(schema)
    response.mimetype = "text/json"
    return response 

@app.route("/mlayer/scales/")
def scales():
    scales = Scale().query.all()
    return render_template("scales.html", scales=scales)


@app.route("/mlayer/aspects/")
def aspects():
    aspects = Aspect().query.all()
    return render_template("aspects.html", aspects=aspects)


@app.route("/taxonomy/export")
def taxonomy_export():
    measurands = MeasurandTaxon.query.all()
    c = Administrative.query.first()
    taxons = []
    for obj in measurands:
        try:
            taxons.append(TaxonomyMapper._getTaxonDict(obj, m_schema))
        except Exception as e:
            print(obj)
            raise e
    xml = TaxonomyMapper._dicttoxml_taxonomy(taxons)
    response = app.make_response(xml)
    response.headers["Content-Disposition"] = "attachment; filename=export_taxonomy.xml"
    response.headers["Content-type"] = "text/xml"
    return response


@app.route("/measurand/<string:measurand_id>/export/xml", methods=["GET", "POST"])
def measurand_export_xml(measurand_id):
    # print("Get Meaurand ", measurand_id)
    m = MeasurandTaxon.query.get_or_404(measurand_id)
    taxon = TaxonomyMapper._getTaxonDict(m, m_schema)
    xml = TaxonomyMapper._dicttoxml_taxon(taxon)
    filename = m.id.replace('.','_')
    content = f'attachment; filename= {filename}.xml'
    response = app.make_response(xml)
    response.headers["Content-Disposition"] = content 
    response.headers["Content-type"] = "text/xml"
    return response 


@app.route("/measurand/<string:measurand_id>/export/json", methods=["GET", "POST"])
def measurand_export_json(measurand_id):
    # print("Get Meaurand ", measurand_id)
    m = MeasurandTaxon.query.get_or_404(measurand_id)
    schema = m_schema.dumps(m, indent=2)
    response = app.make_response(schema)
    response.mimetype = "text/json"
    return response 

@app.route("/measurand/<string:measurand_id>/", methods=["GET", "POST"])
def measurand(measurand_id):
    # print("Get Meaurand ", measurand_id)
    m = MeasurandTaxon.query.get_or_404(measurand_id)
    graph = visualize_model_instance(MeasurandTaxon, m)
    return render_template("measurand.html", measurand=m, graph=graph)


@app.route("/aspect/<string:aspect_id>/", methods=["GET", "POST"])
def aspect(aspect_id):
    # print("Get Aspect ", aspect_id)
    a = Aspect.query.get_or_404(aspect_id)
    a_schema = qk_schema.dumps(a, indent=2)
    # print(a.id)
    mpprint(a_schema)
    graph = visualize_model_instance(Aspect, a)
    return render_template("aspect.html", aspect=a, response=a_schema, graph=graph)


@app.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
def scale(scale_id):
    # print("Get Scale ", scale_id)
    s = Scale.query.get_or_404(scale_id)
    # print(s.id)
    graph = visualize_model_instance(Scale, s)
    return render_template("scale.html", scale=s, graph=graph)


@app.route("/model/mii")
def modelMII():
    models = [Scale, Aspect, Conversion, Transform, MeasurandTaxon, Parameter, Discipline, KcdbCmc]
    excludes = ['Prefix',
                'Unit',
                'Dimension',
                'Taxon',
                'ClassifierTag',
                'Cast',
                'Measurand',
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
    models = [MeasurandTaxon, Parameter, Aspect, Discipline]
    excludes = ['KcdbCmc','Prefix', 'Unit', 'Dimension', 'Conversion', 'Cast', 'Measurand']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/relations")
def modelRelations():
    models = [KcdbCmc, Measurand]
    excludes = ['Taxon', 'Aspect', 'Parameter', 'ClassifierTag']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@app.route("/model/kcdb")
def modelKcdb():
    models = [KcdbCmc, MeasurandTaxon]
    excludes = ['ClassifierTag']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)

