#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from flask import url_for

from flask_admin import Admin 
from flask_admin.theme import Bootstrap4Theme
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView

from miiflask.flask.models.model import Domain

from miiflask.flask.models.kcdb import (
    KcdbCmc,
    KcdbQuantity,
    KcdbArea,
    KcdbBranch,
    KcdbService,
    KcdbSubservice,
    KcdbIndividualService,
    KcdbInstrument,
    KcdbInstrumentMethod,
    KcdbParameter,
    KcdbServiceClass
)

from miiflask.flask.models.taxonomy import (
        MeasurandTaxon,
        Parameter,
        Discipline,
        )

from miiflask.flask.models.mlayer import (
        Aspect,
        Unit,
        Scale,
        Conversion,
        Cast,
        Transform,
        Dimension,
        System,
        Prefix,
        QuantityObject
        )

from miiflask.flask.admin.views import (
        MeasurandView,
        TaxonView,
        MeasurandTaxonView,
        ParameterView,
        CMCView,
        MyModelView,
        KcdbServiceView,
        AspectView,
        ScaleView,
        UnitView,
        CastConversionView,
        QuantityObjectView,
        DimensionView,
        KcdbBranchView
        )

from miiflask.flask.db import Session

class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('main.index')

def init_admin(app):


        admin = Admin(app, name="mii", theme=Bootstrap4Theme(swatch="cerulean"))
        admin.add_view(ModelView(Domain, Session()))
        admin.add_view(AspectView(Aspect, Session(), category="Mlayer"))
        admin.add_view(ScaleView(Scale, Session(), category="Mlayer"))
        admin.add_view(UnitView(Unit, Session(), category="Mlayer"))
        admin.add_view(QuantityObjectView(QuantityObject, Session(), category="Mlayer"))
        admin.add_view(MyModelView(Prefix, Session(), category="Mlayer"))
        admin.add_view(CastConversionView(Conversion, Session(), category="Mlayer"))
        admin.add_view(CastConversionView(Cast, Session(), category="Mlayer"))
        admin.add_view(MyModelView(Transform, Session(), category="Mlayer"))
        admin.add_view(DimensionView(Dimension, Session(), category="Mlayer"))
        admin.add_view(MyModelView(System, Session(), category="Mlayer"))
        admin.add_view(ParameterView(Parameter, Session(), category="Measurand"))
        admin.add_view(MyModelView(Discipline, Session(), category="Measurand"))
        admin.add_view(MeasurandTaxonView(MeasurandTaxon, Session(), category="Measurand"))
        admin.add_view(KcdbServiceView(KcdbServiceClass, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbQuantity, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbArea, Session(), category="KCDB"))
        admin.add_view(KcdbBranchView(KcdbBranch, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbService, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbSubservice, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbIndividualService, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbInstrument, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbInstrumentMethod, Session(), category="KCDB"))
        admin.add_view(MyModelView(KcdbParameter, Session(), category="KCDB"))
        admin.add_view(CMCView(KcdbCmc, Session(), category="KCDB"))
            
        admin.add_link(MainIndexLink(name='Homepage'))
