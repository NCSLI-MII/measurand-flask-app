#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from sqlalchemy import select
from flask import render_template, make_response, url_for
from graphviz import Digraph

from miiflask.flask.main.init import bp
from miiflask.flask.db import (
        get_session, 
        get_or_404, 
        obj_serialize_json
        )

from miiflask.flask.models.kcdb import KcdbCmc, KcdbArea

from miiflask.flask.models.mlayer import ( 
        Aspect,
        Scale,
        Unit,
        Conversion,
        Cast,
        Transform,
        Prefix,
        Dimension,
        System,
        QuantityObject,
        )

from miiflask.flask.models.taxonomy import (
        MeasurandTaxon,
        Parameter,
        Discipline
        )

from miiflask.flask.models.schemas import ( 
        AspectSchema,
        MeasurandTaxonSchema,
        KcdbCmcSchema
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
    statement = select(QuantityObject).order_by(QuantityObject.quantity_name)
    quantities = get_session().scalars(statement).all() 
    return render_template(
        "index.html",
        measurands=measurands,
        aspects=aspects,
        scales=scales,
        quantities=quantities
    )


@bp.route("/mlayer/quantities/")
def quantities():
    statement = select(QuantityObject).order_by(QuantityObject.quantity_name)
    quantities = get_session().scalars(statement).all() 
    return render_template("represented_quantities.html", quantities=quantities)


@bp.route("/mlayer/scales/")
def scales():
    scales = get_session().scalars(select(Scale)).all()
    return render_template("scales.html", scales=scales)


@bp.route("/mlayer/aspects/")
def aspects():
    aspects = get_session().scalars(select(Aspect)).all()
    return render_template("aspects.html", aspects=aspects)


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

#@bp.route("/measurand/<string:measurand_id>/", methods=["GET", "POST"])
#def measurand(measurand_id):
    # print("Get Meaurand ", measurand_id)
    #m = MeasurandTaxon.query.get_or_404(measurand_id)
#    obj = get_or_404(MeasurandTaxon, measurand_id)
#    graph = visualize_model_instance(MeasurandTaxon, obj)
#    return render_template("measurand.html", measurand=obj, graph=graph)

@bp.route("/measurand/<string:measurand_id>/", methods=["GET", "POST"])
def measurand(measurand_id):

    measurand = get_or_404(MeasurandTaxon, measurand_id)

    dot = Digraph(
        "measurand_graph",
        graph_attr={"rankdir": "LR", "splines": "curved"}
    )

    seen_nodes = set()

    def add_node(node_id, label, **attrs):
        if node_id not in seen_nodes:
            dot.node(node_id, label=label, **attrs)
            seen_nodes.add(node_id)

    meas_node = f"meas_{measurand.id}"

    add_node(
        meas_node,
        measurand.name,
        shape="diamond",
        style="filled",
        fillcolor="#FFE082",
        URL=url_for("main.measurand", measurand_id=measurand.id),
        tooltip=f"Measurand: {measurand.name}"
    )

    # ---- DIRECT ASPECT ----

    aspect_node = f"aspect_{measurand.aspect.id}"

    add_node(
        aspect_node,
        measurand.aspect.name,
        shape="box",
        style="filled",
        fillcolor="#BBDEFB",
        URL=url_for("main.aspect", aspect_id=measurand.aspect.id),
        tooltip=f"Aspect: {measurand.aspect.name}"
    )

    dot.edge(
        meas_node,
        aspect_node,
        label="has result",
        color="#1E88E5"
    )

    # ---- PARAMETERS ----
    for param in measurand.parameters:

        param_node = f"param_{param.id}"

        add_node(
            param_node,
            param.name,
            shape="oval",
            style="filled",
            fillcolor="#FFA500",
            tooltip=f"Parameter: {param.aspect.name}",
            URL=url_for("main.aspect", aspect_id=param.aspect.id),
        )

        dot.edge(
            meas_node,
            param_node,
            color="#FFA500"
        )

    legend_label = """<
    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">

    <TR><TD COLSPAN="2"><B>Legend</B></TD></TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#FFE082" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Measurand</TD>
    </TR>
    
    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#BBDEFB" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Aspect</TD>
    </TR>
    
    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#FFA500" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Parameter</TD>
    </TR>


    </TABLE>
    >"""
    # invisible anchor
    dot.node("legend_anchor", "", shape="point", style="invis")

    # legend node
    dot.node(
        "legend",
        label=legend_label,
        shape="plain",
        fontsize="9"
    )

    # connect graph to anchor so it stays below
    dot.edge(meas_node, "legend_anchor", style="invis")


    with dot.subgraph() as s:
        s.attr(rank="sink")
        s.node("legend")
        s.node("legend_anchor")


    return render_template(
        "measurand.html",
        measurand=measurand,
        graph=dot.source
    )

#@bp.route("/aspect/<string:aspect_id>/", methods=["GET", "POST"])
#def aspect(aspect_id):
#    obj = get_or_404(Aspect, aspect_id)
#    schema = aspect_schema.dumps(obj, indent=2)
#    graph = visualize_model_instance(Aspect, obj)
#    return render_template("aspect.html", aspect=obj, response=schema, graph=graph)


@bp.route("/aspect/<aspect_id>")
def aspect(aspect_id):

    aspect  = get_or_404(Aspect, aspect_id)
    dot = Digraph("ontology", graph_attr={"rankdir": "LR"})
    
    aspect_node = f"aspect_{aspect.id}"
    # current node
    dot.node(
        aspect_node,
        label=aspect.name,
        shape="box",
        style="filled",
        fillcolor="#BBDEFB",
        URL=url_for("main.aspect", aspect_id=aspect.id),
        tooltip=f"Aspect: {aspect.name}"
    )

    # connected scales
    for scale in aspect.scales:
        
        scale_node = f"scale_{scale.id}"
        
        dot.node(
            scale_node,
            label=f"{scale.unit.name}",
            shape="ellipse",
            style="filled",
            fillcolor="#C8E6C9",
            URL=url_for("main.scale", scale_id=scale.id),
            tooltip=f"Scale: {scale.unit.name}"
        )

        dot.edge(aspect_node, scale_node, color="#C8E6C9")
    
    legend_label = """<
    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">

    <TR><TD COLSPAN="2"><B>Legend</B></TD></TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#BBDEFB" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Aspect</TD>
    </TR>
    
    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#C8E6C9" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Scale</TD>
    </TR>


    </TABLE>
    >"""
    # invisible anchor
    dot.node("legend_anchor", "", shape="point", style="invis")

    # legend node
    dot.node(
        "legend",
        label=legend_label,
        shape="plain",
        fontsize="9"
    )

    # connect graph to anchor so it stays below
    dot.edge(aspect_node, "legend_anchor", style="invis")


    with dot.subgraph() as s:
        s.attr(rank="sink")
        s.node("legend")
        s.node("legend_anchor")

    return render_template(
        "aspect.html",
        aspect=aspect,
        graph=dot.source
    )


#@bp.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
#def scale(scale_id):
#    obj = get_or_404(Scale, scale_id)
#    graph = visualize_model_instance(Scale, obj)
#    return render_template("scale.html", scale=obj, graph=graph)


@bp.route("/quantity-object/<string:aspect_id>/<string:scale_id>")
def quantity_object_detail(aspect_id, scale_id):
    session = get_session() 
    qo = session.get(
        QuantityObject,
        {
            "scale_id": scale_id,
            "aspect_id": aspect_id,
        }
    )

    if qo is None:
        abort(404)

    dot = Digraph(
        "qo_graph",
        graph_attr={"rankdir": "LR", "splines": "curved"}
    )

    qo_node = f"qo_{qo.aspect.id}_{qo.scale_id}"

    dot.node(
        qo_node,
        label=f"{qo.quantity_name}",
        shape="ellipse",
        style="filled",
        fillcolor="#C8E6C9",
        #URL=url_for("main.scale", scale_id=qo.scale.id),
        #tooltip=f"Scale: {qo.scale.unit.name or qo.scale.unit.symbol}"
    )

    # ---- SCALE ----
    if qo.scale:

        scale_node = f"scale_{qo.scale.id}"

        dot.node(
            scale_node,
            label=f"({qo.scale.scale_type}) {qo.scale.unit.name or qo.scale.unit.symbol}",
            shape="ellipse",
            style="filled",
            fillcolor="#C8E6C9",
            URL=url_for("main.scale", scale_id=qo.scale.id),
            tooltip=f"Scale: {qo.scale.unit.name or qo.scale.unit.symbol}"
        )
        
        dot.edge(
            scale_node,
            qo_node,
            #label="has unit",
            color="#FFE0B2"
        )
    if qo.aspect:
        aspect_node = f"aspect_{qo.aspect.id}"
        # current node
        dot.node(
            aspect_node,
            label=qo.aspect.name,
            shape="box",
            style="filled",
            fillcolor="#BBDEFB",
            URL=url_for("main.aspect", aspect_id=qo.aspect.id),
            tooltip=f"Aspect: {qo.aspect.name}"
        )
        dot.edge(
            aspect_node,
            qo_node,
            #label="has aspect",
            color="#1E88E5"
        )
    # ---- CONVERSIONS ----
    for target in qo.transformations:
            dst_qo = session.get(
                QuantityObject,
                {
                    "scale_id": target.dst_scale_id,
                    "aspect_id": target.dst_aspect_id,
                }
            )
            target_node = f"qo_{dst_qo.quantity_name}"

            dot.node(
                target_node,
                label=f"{dst_qo.quantity_name}",
                shape="ellipse",
                style="filled",
                fillcolor="#E1BEE7",
                URL=url_for("main.quantity_object_detail", aspect_id=dst_qo.aspect_id, scale_id=dst_qo.scale_id),
                tooltip=f"Transforms to: {dst_qo.name}"
            )

            dot.edge(
                qo_node,
                target_node,
                #label="converts to",
                style="dashed",
                color="#8E24AA"
            )
    return render_template("quantity_object_detail.html", quantity_object=qo, graph=dot.source)

@bp.route("/scale/<string:scale_id>/", methods=["GET", "POST"])
def scale(scale_id):

    scale = get_or_404(Scale, scale_id)

    dot = Digraph(
        "scale_graph",
        graph_attr={"rankdir": "LR", "splines": "curved"}
    )

    scale_node = f"scale_{scale.id}"

    dot.node(
        scale_node,
        label=f"({scale.scale_type}) {scale.unit.name or scale.unit.symbol}",
        shape="ellipse",
        style="filled",
        fillcolor="#C8E6C9",
        URL=url_for("main.scale", scale_id=scale.id),
        tooltip=f"Scale: {scale.unit.name or scale.unit.symbol}"
    )

    # ---- UNIT ----
    if scale.unit:

        unit_node = f"unit_{scale.unit.id}"

        dot.node(
            unit_node,
            label=f"{scale.unit.name or scale.unit.symbol}",
            shape="hexagon",
            style="filled",
            fillcolor="#FFE0B2",
            URL=url_for("main.unit", unit_id=scale.unit.id),
            tooltip=f"Unit: {scale.unit.name or scale.unit.symbol}"
        )
        
        dot.edge(
            scale_node,
            unit_node,
            #label="has unit",
            color="#FFE0B2"
        )

    # ---- ASPECTS ----
    for aspect in scale.aspects:

        aspect_node = f"aspect_{aspect.id}"

        dot.node(
            aspect_node,
            label=aspect.name,
            shape="box",
            style="filled",
            fillcolor="#BBDEFB",
            URL=url_for("main.aspect", aspect_id=aspect.id),
            tooltip=f"Aspect: {aspect.name}"
        )

        dot.edge(
            scale_node,
            aspect_node,
            #label="has aspect",
            color="#1E88E5"
        )

        # ---- CONVERSIONS ----
        for target in scale.conversions:
            if (target.src_aspect_id == aspect.id):
                target_node = f"scale_{target.dst_scale_id}"

                dot.node(
                    target_node,
                    label=f"({target.dst_scale.scale_type}) {target.dst_scale.unit.name}",
                    shape="ellipse",
                    style="filled",
                    fillcolor="#E1BEE7",
                    URL=url_for("main.scale", scale_id=target.dst_scale_id),
                    tooltip=f"Convertible scale: {target.dst_scale_id}"
                )

                dot.edge(
                    aspect_node,
                    target_node,
                    #label="converts to",
                    style="dashed",
                    color="#8E24AA"
                )
        # ---- CASTS ----
        for target in scale.casts:
            
            if (target.src_aspect_id == aspect.id):
                dst_aspect_node = f"cast_{target.dst_aspect_id}"
                target_node = f"cast_scale_{target.dst_scale_id}"

                dot.node(
                    dst_aspect_node,
                    label=f"({target.dst_aspect.name})",
                    shape="box",
                    style="filled",
                    fillcolor="#BBDEFB",
                    URL=url_for("main.aspect", aspect_id=target.dst_aspect_id),
                    tooltip=f"Castable aspect: {target.dst_aspect_id}"
                )
                
                dot.edge(
                    aspect_node,
                    dst_aspect_node,
                    #label="converts to",
                    style="dashed",
                    color="#1E88E5"
                )

                dot.node(
                    target_node,
                    label=f"({target.dst_scale.scale_type}) {target.dst_scale.unit.name}",
                    shape="ellipse",
                    style="filled",
                    fillcolor="#E1BEE7",
                    URL=url_for("main.scale", scale_id=target.dst_scale_id),
                    tooltip=f"Castable scale: {target.dst_scale_id}"
                )
                dot.edge(
                    dst_aspect_node,
                    target_node,
                    #label="converts to",
                    style="dashed",
                    color="#8E24AA"
                )

    legend_label = """<
    <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">

    <TR><TD COLSPAN="2"><B>Legend</B></TD></TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#C8E6C9" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Scale</TD>
    </TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#BBDEFB" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Aspect</TD>
    </TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#FFE0B2" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Unit</TD>
    </TR>

    <TR>
    <TD>
    <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0">
    <TR><TD BGCOLOR="#E1BEE7" WIDTH="24" HEIGHT="14"></TD></TR>
    </TABLE>
    </TD>
    <TD ALIGN="LEFT">Transformation</TD>
    </TR>

    </TABLE>
    >"""
    # invisible anchor
    dot.node("legend_anchor", "", shape="point", style="invis")

    # legend node
    dot.node(
        "legend",
        label=legend_label,
        shape="plain",
        fontsize="9"
    )

    # connect graph to anchor so it stays below
    dot.edge(scale_node, "legend_anchor", style="invis")


    with dot.subgraph() as s:
        s.attr(rank="sink")
        s.node("legend")
        s.node("legend_anchor")


    return render_template(
        "scale.html",
        scale=scale,
        graph=dot.source
    )


@bp.route("/unit/<string:unit_id>/", methods=["GET", "POST"])
def unit(unit_id):
    u = get_or_404(Unit, unit_id)
    return render_template("unit.html", unit=u)

@bp.route("/model/mii")
def modelMII():
    models = [Scale, Aspect, Conversion, Transform, MeasurandTaxon, Parameter, Discipline, KcdbCmc, QuantityObject]
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

@bp.route("/model/mlayer/quantity")
def modelQuantity():
    models = [QuantityObject, Aspect, Scale, Unit, Prefix, Dimension, System]
    excludes = ['Conversion', 'Cast']
    graph = generate_data_model_diagram(models, excludes)
    return render_template("diagram.html", graph=graph)

@bp.route("/model/mlayer/scale")
def modelMlayerScale():
    models = [Scale, Unit, Prefix, Dimension, System, QuantityObject]
    excludes = ['Aspect', 'Conversion', 'Cast']
    graph = generate_data_model_diagram(models, excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/mlayer/conversion")
def modelMlayerConversion():
    models = [Conversion, Aspect, Scale, Transform, QuantityObject]
    excludes = ['Prefix', 'Unit', 'Dimension', 'Cast']
    graph = generate_data_model_diagram(models, excludes=excludes)
    return render_template("diagram.html", graph=graph)


@bp.route("/model/mlayer/cast")
def modelMlayerCast():
    models = [Cast, Aspect, Scale, Transform, QuantityObject]
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

