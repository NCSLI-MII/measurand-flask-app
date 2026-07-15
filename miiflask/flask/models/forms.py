#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from flask import Blueprint, render_template, flash, request
from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    TextAreaField,
    BooleanField,
    SelectField,
    FieldList,
    FormField,
    SubmitField
)

from wtforms.validators import DataRequired, Optional, Length

from markupsafe import Markup
import xmltodict

from miiflask.flask.db import (
        get_session
        )

from miiflask.flask.models import (
    MeasurandTaxon,
    Aspect,
    Discipline,
    Parameter,
    Reference
)
from miiflask.flask.models.schemas import MeasurandTaxonSchema


class ParameterForm(FlaskForm):
    name = StringField(
        "Parameter name",
        validators=[DataRequired(), Length(max=50)]
    )

    quantity = StringField(
        "Parameter quantity",
        validators=[Optional(), Length(max=50)]
    )

    aspect_id = SelectField(
        "Parameter aspect",
        choices=[],
        validators=[Optional()]
    )

    definition = TextAreaField(
        "Parameter definition",
        validators=[Optional()]
    )

    class Meta:
        csrf = False


class ReferenceForm(FlaskForm):
    category_name = StringField(
        "Reference category name",
        validators=[Optional(), Length(max=100)]
    )
    
    category_value = StringField(
        "Reference category value",
        validators=[Optional(), Length(max=100)]
    )

    reference_url = StringField(
        "Reference URL",
        validators=[Optional()]
    )

    reference_name = StringField(
        "Reference Name",
        validators=[Optional()]
    )

    class Meta:
        csrf = False


class MeasurandForm(FlaskForm):
    
    existing_measurand_id = SelectField(
        "Load existing measurand",
        choices=[],
        validators=[Optional()],
        coerce=lambda x: str(x) if x else None
    )


    id = StringField(
        "ID",
        validators=[DataRequired()]
    )

    name = StringField(
        "Name",
        validators=[DataRequired(), Length(max=50)]
    )

    definition = TextAreaField(
        "Definition",
        validators=[Optional()]
    )

    deprecated = BooleanField(
        "Deprecated"
    )

    replacement = StringField(
        "Replacement",
        validators=[Optional(), Length(max=50)]
    )

    #quantitykind = StringField(
    #    "Quantity kind",
    #    validators=[Optional(), Length(max=50)]
    #)

    #aspect_id = SelectField(
    #    "Measurand aspect",
    #    choices=[],
    #    validators=[Optional()]
    #)

    processtype = SelectField(
        "Process type",
        choices=[
            ("", ""),
            ("Source", "Source"),
            ("Measure", "Measure")
        ],
        validators=[Optional()]
    )

    qualifier = StringField(
        "Qualifier",
        validators=[Optional(), Length(max=50)]
    )

    result = StringField(
        "Result",
        validators=[DataRequired(), Length(max=50)]
    )

    result_quantity = StringField(
        "Result quantity",
        validators=[Optional(), Length(max=50)]
    )

    result_aspect_id = SelectField(
        "Result aspect",
        choices=[],
        validators=[Optional()]
    )

    discipline_id = SelectField(
        "Discipline",
        choices=[],
        validators=[Optional()]
    )

    parameters = FieldList(
        FormField(ParameterForm),
        min_entries=1,
        max_entries=20
    )

    external_references = FieldList(
        FormField(ReferenceForm),
        min_entries=1,
        max_entries=20
    )

    generate_xml = SubmitField("Generate XML")


