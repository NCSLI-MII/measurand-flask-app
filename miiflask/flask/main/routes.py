#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from sqlalchemy import select
from flask import render_template, make_response

from miiflask.flask.main.init import bp
from miiflask.flask.db import (
        get_session, 
        get_or_404, 
        obj_serialize_json
        )

from miiflask.flask.model import ( 
        MeasurandTaxon,
        KcdbCmc,
        Aspect,
        Scale,
        Unit,
        Conversion,
        Cast,
        Transform,
        Parameter,
        Discipline,
        Prefix,
        Dimension,
        System
        )

from miiflask.flask.model import ( 
        KcdbCmcSchema,
        AspectSchema,
        MeasurandTaxonSchema
        )

from miiflask.utils.model_visualizer import (
    generate_data_model_diagram,
    visualize_model_instance
    )

from miiflask.mappers.taxonomy_mapper_v2 import TaxonomyMapper

cmc_schema = KcdbCmcSchema()
aspect_schema = AspectSchema()
measurand_schema = MeasurandTaxonSchema()

@bp.route("/")
def index():
    #meta = db.session.info
    #print(meta)
    session = get_session() 
    measurands = session.scalars(select(MeasurandTaxon)).all()
    aspects = session.scalars(select(Aspect)).all()
    scales = session.scalars(select(Scale)).all()
    return render_template(
        "index.html",
        measurands=measurands,
        aspects=aspects,
        scales=scales,
    )

@bp.route("/taxonomy/")
def taxonomy():
    measurands = get_session().scalars(select(MeasurandTaxon)).all()
    return render_template("taxonomy.html", measurands=measurands)


@bp.route("/kcdbcmcs/")
def kcdbcmcs():
    cmcs = get_session().scalars(select(KcdbCmc)).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/export/json")
def kcdbcmcs_export_json():
    cmcs = get_sesion().scalars(select(KcdbCmc)).all()
    schema = cmc_schema.dumps(cmcs, many=True, indent=4)
    response = bp.make_response(schema)
    response.headers["Content-Disposition"] = "attachment; filename=export_cmcs.json"
    response.headers["Content-type"] = "text/json"
    return response 


@bp.route("/kcdbcmcs/auv/")
def kcdbcmcs_auv():

    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "AUV")
    )

    cmcs = session.scalars(stmt).all()

    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/em/")
def kcdbcmcs_em():
    
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "EM")
    )

    cmcs = session.scalars(stmt).all()
    
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/l/")
def kcdbcmcs_l():
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "L")
    )

    cmcs = session.scalars(stmt).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/m/")
def kcdbcmcs_m():
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "M")
    )

    cmcs = session.scalars(stmt).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/pr/")
def kcdbcmcs_pr():
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "PR")
    )

    cmcs = session.scalars(stmt).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/t/")
def kcdbcmcs_t():
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "T")
    )

    cmcs = session.scalars(stmt).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmcs/tf/")
def kcdbcmcs_tf():
    session = get_session()

    stmt = select(KcdbCmc).where(
        KcdbCmc.area.has(KcdbArea.label == "TF")
    )

    cmcs = session.scalars(stmt).all()
    return render_template("kcdbcmcs.html", cmcs=cmcs)


@bp.route("/kcdbcmc/<string:kcdbcmc_id>/export/json", methods=["GET", "POST"])
def kcdbcmc_export_json(kcdbcmc_id):
    # print("Get Meaurand ", measurand_id)
    cmc = get_or_404(KcdbCmc, kcdbcmc_id)
    schema = cmc_schema.dumps(cmc, indent=2)
    response = make_response(schema)
    response.mimetype = "text/json"
    return response 


@bp.route("/mlayer/scales/")
def scales():
    scales = get_session().scalars(select(Scale)).all()
    return render_template("scales.html", scales=scales)


@bp.route("/mlayer/aspects/")
def aspects():
    aspects = get_session().scalars(select(Aspect)).all()
    return render_template("aspects.html", aspects=aspects)


@bp.route("/taxonomy/export")
def taxonomy_export():
    measurands = get_session().scalars(select(MeasurandTaxon)).all()
    taxons = []
    for obj in measurands:
        try:
            taxons.append(TaxonomyMapper._getTaxonDict(obj, measurand_schema))
        except Exception as e:
            print(obj)
            raise e
    xml = TaxonomyMapper._dicttoxml_taxonomy(taxons)
    response = make_response(xml)
    response.headers["Content-Disposition"] = "attachment; filename=export_taxonomy.xml"
    response.headers["Content-type"] = "text/xml"
    return response


@bp.route("/measurand/<string:measurand_id>/export/xml", methods=["GET", "POST"])
def measurand_export_xml(measurand_id):
    # print("Get Meaurand ", measurand_id)
    obj = get_or_404(MeasurandTaxon, measurand_id)
    taxon = TaxonomyMapper._getTaxonDict(obj, measurand_schema)
    xml = TaxonomyMapper._dicttoxml_taxon(taxon)
    filename = obj.name.replace('.','_')
    content = f'attachment; filename= {filename}.xml'
    response = make_response(xml)
    response.headers["Content-Disposition"] = content 
    response.headers["Content-type"] = "text/xml"
    return response 

@bp.route("/measurand/<string:measurand_id>/", methods=["GET", "POST"])
def measurand(measurand_id):
    # print("Get Meaurand ", measurand_id)
    #m = MeasurandTaxon.query.get_or_404(measurand_id)
    obj = get_or_404(MeasurandTaxon, measurand_id)
    graph = visualize_model_instance(MeasurandTaxon, obj)
    return render_template("measurand.html", measurand=obj, graph=graph)


@bp.route("/aspect/<string:aspect_id>/", methods=["GET", "POST"])
def aspect(aspect_id):
    obj = get_or_404(Aspect, aspect_id)
    schema = aspect_schema.dumps(obj, indent=2)
    graph = visualize_model_instance(Aspect, obj)
    return render_template("aspect.html", aspect=obj, response=schema, graph=graph)

@bp.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
def scale(scale_id):
    obj = get_or_404(Scale, scale_id)
    graph = visualize_model_instance(Scale, obj)
    return render_template("scale.html", scale=obj, graph=graph)

@bp.route("/unit/<string:unit_id>/", methods=["GET", "POST"])
def unit(unit_id):
    u = get_or_404(Unit, unit_id)
    return render_template("unit.html", unit=u)

@bp.route("/model/mii")
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


@bp.route("/model/mlayer/scale")
def modelMlayerScale():
    models = [Scale, Unit, Prefix, Dimension, System]
    excludes = ['Aspect', 'Conversion', 'Cast']
    graph = generate_data_model_diagram(models, excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/mlayer/conversion")
def modelMlayerConversion():
    models = [Conversion, Aspect, Scale, Transform]
    excludes = ['Prefix', 'Unit', 'Dimension', 'Cast']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/mlayer/cast")
def modelMlayerCast():
    models = [Cast, Aspect, Scale, Transform]
    excludes = ['Prefix', 'Unit', 'Dimension', 'Conversion']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/taxonomy/measurand")
def modelTaxonomyMeasurand():
    models = [MeasurandTaxon, Parameter, Aspect, Discipline]
    excludes = ['KcdbCmc','Prefix', 'Unit', 'Dimension', 'Conversion', 'Cast', 'Measurand']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/relations")
def modelRelations():
    models = [KcdbCmc, Measurand]
    excludes = ['Taxon', 'Aspect', 'Parameter', 'ClassifierTag']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/kcdb")
def modelKcdb():
    models = [KcdbCmc, MeasurandTaxon]
    excludes = ['ClassifierTag']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)

