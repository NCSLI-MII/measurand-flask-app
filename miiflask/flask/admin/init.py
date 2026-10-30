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
        ConversionCast,
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
        ConversionCastView,
        QuantityObjectView,
        DimensionView,
        KcdbBranchView
        )


class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('main.index')

def init_admin(app):
    session = app.extensions["miiflask"]["session_factory"]

    admin = Admin(app, name="mii", theme=Bootstrap4Theme(swatch="cerulean"))
    admin.add_view(ModelView(Domain, session))
    admin.add_view(AspectView(Aspect, session, category="Mlayer"))
    admin.add_view(ScaleView(Scale, session, category="Mlayer"))
    admin.add_view(UnitView(Unit, session, category="Mlayer"))
    admin.add_view(QuantityObjectView(QuantityObject, session, category="Mlayer"))
    admin.add_view(MyModelView(Prefix, session, category="Mlayer"))
    #admin.add_view(CastConversionView(Conversion, session, category="Mlayer"))
    #admin.add_view(CastConversionView(Cast, session, category="Mlayer"))
    admin.add_view(
            ConversionCastView(
                ConversionCast,
                session,
                name="Conversions / Casts",
                endpoint="conversioncast",
                category="Mlayer"
                )
            )

    admin.add_view(MyModelView(Transform, session, category="Mlayer"))
    admin.add_view(DimensionView(Dimension, session, category="Mlayer"))
    admin.add_view(MyModelView(System, session, category="Mlayer"))
    admin.add_view(ParameterView(Parameter, session, category="Measurand"))
    admin.add_view(MyModelView(Discipline, session, category="Measurand"))
    admin.add_view(MeasurandTaxonView(MeasurandTaxon, session, category="Measurand"))
    admin.add_view(KcdbServiceView(KcdbServiceClass, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbQuantity, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbArea, session, category="KCDB"))
    admin.add_view(KcdbBranchView(KcdbBranch, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbService, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbSubservice, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbIndividualService, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbInstrument, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbInstrumentMethod, session, category="KCDB"))
    admin.add_view(MyModelView(KcdbParameter, session, category="KCDB"))
    admin.add_view(CMCView(KcdbCmc, session, category="KCDB"))
        
    admin.add_link(MainIndexLink(name='Homepage'))
