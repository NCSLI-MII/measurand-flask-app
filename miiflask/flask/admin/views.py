#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
import logging
from urllib.parse import urlparse

from flask import url_for

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import Bootstrap4Theme
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
from miiflask.flask.model import (
        AspectSchema,
        MeasurandTaxonSchema, 
        KcdbCmcSchema, 
        UnitSchema, 
        ScaleSchema, 
        SystemSchema
        )
log = logging.getLogger("flask-admin.sqla")

qk_schema = AspectSchema()
aspects_schema = AspectSchema(many=True)
scale_schema = ScaleSchema()
scales_schema = ScaleSchema(many=True)
unit_schema = UnitSchema()
units_schema = UnitSchema(many=True)
system_schema = SystemSchema()
systems_schema = SystemSchema(many=True)
m_schema = MeasurandTaxonSchema()
measurands_schema = MeasurandTaxonSchema(many=True)
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


def is_url(url_string):
    try:
        result = urlparse(url_string)
        # Check if scheme and domain present
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def _ref_formatter(view, context, model, name):
        if is_url(model.reference):
            return Markup('<a href="{}"> {} '.format(model.reference, model.reference))
        else:
            return model.reference





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

                #self.session.bulk_update_mappings(KcdbCmc, _update_mappings)
                self.session.commit()
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
           "discipline",
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
                    'discipline',
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
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('scale.details_view', id=model.systematic_scale_id)
        return Markup('<a href="{}">{}</a>'.format(url, field))

    def _exponents_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        exponents = field.strip('[]').split(',') 
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
                           "systematic_scale",
                           "exponents")
    column_formatters = {"id": _id_formatter,
                         "formal_system": _link_system_formatter,
                         "systematic_scale": _link_scale_formatter,
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
        aspects = {}
        for s in model.conversions: aspects[s.aspect.id]=(s.aspect.name,[]) 
        for s in model.conversions:
            
            url_aspect = url_for('aspect.details_view', id=s.aspect.id)
            url_src = url_for('scale.details_view', id=s.src_scale.id)
            url_dst = url_for('scale.details_view', id=s.dst_scale.id)
            name_ = '{}: {} &#8594 {}'.format(s.aspect.name,
                                    s.src_scale.ml_name,
                                    s.dst_scale.ml_name)
            id_ = '{},{},{}'.format(s.src_scale.id,s.dst_scale.id,s.aspect.id)

            
            url = url_for('conversion.details_view', id=id_)
            url_details = (
                    '<a href={}>{}</a> &#8594 <a href={}>{}</a> <a href="{}">{}</a>'.format(
                        url_src,
                        s.src_scale.ml_name,
                        url_dst,
                        s.dst_scale.ml_name,
                        url,"(see details)"
                        )
                    )
            aspects[s.aspect.id][1].append(url_details)
            urls.append(url_details)
        markup=""
        
        for a in aspects:
            url_aspect = url_for('aspect.details_view', id=a)
            markup += f'<a href={url_aspect}>{a}: {aspects[a][0]}</a><br/>'
            markup += ('<br/>').join(aspects[a][1])
            markup += ('<br/><br/>')

        return Markup(markup)

    def _cast_link_formatter(view, context, model, name):
        urls = []
        for s in model.casts:
            name_ = '{}: {} &#8594 {}: {}'.format(s.src_aspect.name,
                                       s.src_scale.ml_name,
                                       s.dst_aspect.name,
                                       s.dst_scale.ml_name)
            id_ = '{},{},{},{}'.format(s.src_scale.id,s.dst_scale.id,s.src_aspect.id,s.dst_aspect.id)
            url = url_for('cast.details_view', id=id_)
            urls.append('<a href="{}">{}</a>'.format(url,name_))
                                                     #id_.replace(',', '.')))
        return Markup((', <br/>').join(urls))
    
    column_searchable_list = ['ml_name', 'id', 'unit.name']
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {
            'id': _id_formatter,
            'unit': _link_formatter,
            'prefix': _link_formatter,
            'root_scale_id': _root_link_formatter,
            'conversions': _cnv_link_formatter,
            'casts': _cast_link_formatter,
            'system_dimensions': _link_dim_formatter
            }
    column_list = ("id",
                   "ml_name",
                   "unit")
    column_details_list = ("id",
                           "ml_name",
                           'scale_type',
                           "unit",
                           'root_scale_id',
                           'prefix',
                           "ref_point",
                           "ref_point_l",
                           "ref_point_h",
                           "system_dimensions",
                           "is_systematic",
                           "is_special",
                           "conversions",
                           "casts",
                           )


class UnitView(MyModelView):
    

    page_size = 100
    can_view_details = True
    column_display_pk = True
    column_hide_backrefs = False
    column_formatters = {
            'id': _id_formatter,
            'reference': _ref_formatter
            }

class CastConversionView(MyModelView):
    
    def _aspect_link_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('aspect.details_view', id=field.id)
        return Markup('<a href="{}">{}</a>'.format(url, field))
    
    def _scale_link_formatter(view, context, model, name):
        field = getattr(model, name)
        if field is None:
            return u""
        url = url_for('scale.details_view', id=field.id)
        return Markup('<a href="{}">{}</a>'.format(url, field))
    
    column_formatters = {
            'src_scale': _scale_link_formatter,
            'dst_scale': _scale_link_formatter,
            'aspect': _aspect_link_formatter,
            'src_aspect': _aspect_link_formatter,
            'dst_aspect': _aspect_link_formatter,
            'transform': _link_formatter
            }


class AspectView(MyModelView):

    def _scale_formatter(view, context, model, name):
        urls = []
        for s in model.scales:
            url = url_for('scale.details_view', id=s.id)
            urls.append('<a href="{}">{}: {}</a>'.format(url, s.id, s.ml_name))
        return Markup(('<br/>').join(urls))
    

    column_searchable_list = ['name']
    can_export = True
    column_display_pk = True
    can_view_details = True
    column_hide_backrefs = False
    column_formatters = {'id': _id_formatter,
                         'scales': _scale_formatter,
                         'reference': _ref_formatter}
    column_list = ("id",
                   "name",
                   "ml_name",
                   "scales")
    column_details_list = ("id",
                           "name",
                           "ml_name",
                           "scales",
                           "reference"
                           )
