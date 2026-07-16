#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from datetime import datetime
from typing import Optional
from enum import Enum
import html
import textwrap
from decimal import Decimal
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Integer, Numeric, Boolean, JSON, ForeignKey, LargeBinary, Text, UniqueConstraint, CheckConstraint, text as sql_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipDirection

import graphviz
import os
import re
import base64
import json
from html import escape
from flask import url_for

from miiflask.utils.unicode_mapper import greek_alphabet_unicode, superscript_integers_unicode

Base = declarative_base()
def wrap_comment(text, width=50): 
    #text = html.escape(text) 
    #text = textwrap.dedent(text)
    # The text you want to wrap

    # Wrap the text at 20 characters per line
    wrapped_lines = textwrap.wrap(text, width)

    # Build HTML string dynamically using the align attribute
    #return "<<BR/>" + "<BR/>".join([f"{line}<BR ALIGN=\"LEFT\"/>" for line in wrapped_lines]) + ">"

    return "<BR ALIGN=\"LEFT\"/>".join(textwrap.wrap(text, width))


def relationship_type(rel):
    """
    Return a simple relationship type label.
    """

    if rel.secondary is not None:
        return "many-to-many"

    if rel.direction == RelationshipDirection.ONETOMANY:
        if rel.uselist:
            return "one-to-many"
        return "one-to-one"

    if rel.direction == RelationshipDirection.MANYTOONE:
        return "many-to-one"

    if rel.direction == RelationshipDirection.MANYTOMANY:
        return "many-to-many"

    return "unknown"

def relationship_optionality(rel):
    """
    Determine whether the FK side appears optional or required.

    Returns:
        "optional", "required", or "unknown"
    """

    if not rel.local_columns:
        return "unknown"

    nullable_values = [column.nullable for column in rel.local_columns]

    if any(nullable_values):
        return "optional"

    return "required"

def relationship_symbols(rel):
    """
    Return cardinality symbols for source and target.

    Example:
        Taxon -> Parameter = ("1", "0..*")
        Parameter -> Taxon = ("0..*", "1")
    """

    optionality = relationship_optionality(rel)

    if rel.secondary is not None:
        return "0..*", "0..*"

    if rel.direction == RelationshipDirection.ONETOMANY:
        if rel.uselist:
            return "1", "0..*"
        return "1", "0..1"

    if rel.direction == RelationshipDirection.MANYTOONE:
        target_symbol = "0..1" if optionality == "optional" else "1"
        return "0..*", target_symbol

    if rel.direction == RelationshipDirection.MANYTOMANY:
        return "0..*", "0..*"

    return "?", "?"


def relationship_label(rel):
    """
    Build a label for the diagram edge.
    """

    rel_type = relationship_type(rel)
    left_symbol, right_symbol = relationship_symbols(rel)

    return f"{rel.key} ({left_symbol} to {right_symbol}, {rel_type})"


def relationship_dedupe_key(source_class, rel):
    """
    Create a stable key to avoid drawing both sides of the same relationship.
    """

    source_name = source_class.__name__
    target_name = rel.mapper.class_.__name__

    class_pair = tuple(sorted([source_name, target_name]))

    if rel.back_populates:
        relationship_pair = tuple(sorted([rel.key, rel.back_populates]))
    elif rel.backref:
        relationship_pair = tuple(sorted([rel.key, str(rel.backref)]))
    else:
        relationship_pair = (rel.key,)

    secondary_name = rel.secondary.name if rel.secondary is not None else None

    return class_pair + relationship_pair + (secondary_name,)


def inspect_relationship_edges(model_classes):
    """
    Inspect selected SQLAlchemy model classes and return relationship edges
    suitable for a diagram.
    """

    edges = []
    seen = set()

    selected_class_names = {model_class.__name__ for model_class in model_classes}

    for model_class in model_classes:
        mapper = inspect(model_class)

        for rel in mapper.relationships:
            target_class = rel.mapper.class_
            target_name = target_class.__name__
            source_name = model_class.__name__

            # Only include relationships where both sides are in the selected set
            if target_name not in selected_class_names:
                continue

            dedupe_key = relationship_dedupe_key(model_class, rel)

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            left_symbol, right_symbol = relationship_symbols(rel)

            edge = {
                "source": source_name,
                "target": target_name,
                "relationship_name": rel.key,
                "relationship_type": relationship_type(rel),
                "source_cardinality": left_symbol,
                "target_cardinality": right_symbol,
                "label": relationship_label(rel),
                "back_populates": rel.back_populates,
                "secondary": rel.secondary.name if rel.secondary is not None else None,
            }

            edges.append(edge)

    return edges


def escape_graphviz_label(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("|", "\\|")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("\n", "\\n")
    )

def generate_data_model_diagram(models, excludes=[], detail_level=None, show_attributes=True, add_labels=True, view_diagram=True):
    # Initialize graph with more advanced visual settings
    dot = graphviz.Digraph(comment='Interactive Data Models', format='svg', 
                            graph_attr={'bgcolor': '#EEEEEE', 'rankdir': 'TB', 'splines': 'spline'},
                            node_attr={'shape': 'none', 'fontsize': '10', 'fontname': 'Roboto'},
                            edge_attr={'fontsize': '10', 'fontname': 'Roboto'})
    # Iterate through each SQLAlchemy model
    seen = set()

    for model in models:
        insp = inspect(model)
        name = insp.class_.__name__
        table_comment = escape_graphviz_label(model.__table__.comment or "")
    
        if table_comment:
            node_label = f"{name}|{table_comment}"
        else:
            node_label = f"{name}"
        max_comment_len = 0 
        for column in insp.columns: 
            comment = column.comment or "" 
            max_comment_len = max(max_comment_len, len(comment))        
        
        char_px = 6 
        min_width = 100 
        max_width = 300
        desc_width = max(min_width, min(max_width, max_comment_len * char_px))
        
        # Create an HTML-like label for each model as a rich table
        label = f'''<
        <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
        '''
        if show_attributes is True:         
            label += f'''
            <TR>
            <TD COLSPAN="4" BGCOLOR="#3F51B5">
            <FONT COLOR="white"><B>{escape(name)}</B></FONT>
            </TD>
            </TR>
            '''
            if table_comment:
                label += f'''
                <TR>
                    <TD COLSPAN="4" BGCOLOR="#F5F5F5" ALIGN="LEFT">
                        <FONT POINT-SIZE="8">{table_comment}</FONT>
                    </TD>
                </TR>
                '''
            label += f'''
            <TR>
            <TD BGCOLOR="#E8EAF6" WIDTH="65"><B>Attribute</B></TD>
            <TD BGCOLOR="#E8EAF6"><B>Key</B></TD>
            <TD BGCOLOR="#E8EAF6"><B>Detail</B></TD>
            <TD BGCOLOR="#E8EAF6"><B>Description</B></TD>
            </TR>
            '''
 
            for column in insp.columns:
                comment = wrap_comment(column.comment or "")
                detail = None
                if column.doc:
                    detail = column.doc
                if detail_level:
                    if detail_level == 'core':
                        if detail != detail_level:
                            continue
                constraints = []
                if column.primary_key:
                    constraints.append("PK")
                if column.unique:
                    constraints.append("Unique")
                if column.index:
                    constraints.append("Index")
                if column.foreign_keys:
                    constraints.append("FK")
                
                constraint_str = ','.join(constraints)
                if column.primary_key:
                    color = "#C8E6C9"
                elif column.foreign_keys:
                    color = "#FFF9C4"
                else:
                    color = "#BBDEFB"
                
                #label += f'''<TR>
                #             <TD BGCOLOR="{color}">{column.name} ({constraint_str})</TD>
                #             </TR>'''
                label += f'''<TR>
                <TD ALIGN="LEFT" WIDTH="65" BGCOLOR="{color}">{column.name}</TD>
                <TD ALIGN="LEFT" WIDTH="30" BGCOLOR="{color}">{constraint_str}</TD>
                <TD ALIGN="LEFT" WIDTH="30" BGCOLOR="{color}">{detail}</TD>
                <TD ALIGN="LEFT" WIDTH="{desc_width}">{comment}</TD>
                </TR>'''
        else:
            label += f'''<TR>
            <TD WIDTH="{desc_width}" HEIGHT="50" BGCOLOR="#3F51B5"><FONT COLOR="white">{name}</FONT></TD></TR>
            '''


        label += '</TABLE>>'
        #tooltip = table_comment or f"Table: {name}" 
        dot.node(name, label=label)

        # Add relationships with tooltips and advanced styling
        #for rel in insp.relationships:
        #    target_name = rel.mapper.class_.__name__
        #    if target_name in excludes:
        #        continue
        #    tooltip = f"Relation between {name} and {target_name}"
        #    dot.edge(name, target_name, label=rel.key if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
        # Add relationships with tooltips, cardinality, de-duplication, and styling
        for rel in insp.relationships:
            target_class = rel.mapper.class_
            target_name = target_class.__name__

            if target_name in excludes:
                continue

            dedupe_key = relationship_dedupe_key(model, rel)

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            source_cardinality, target_cardinality = relationship_symbols(rel)
            rel_type = relationship_type(rel)

            edge_label = rel.key if add_labels else None

            tooltip = (
                f"Relation between {name} and {target_name}\n"
                f"Relationship: {rel.key}\n"
                f"Type: {rel_type}\n"
                f"Cardinality: {source_cardinality} to {target_cardinality}"
            )

            dot.edge(
                name,
                target_name,
                label=edge_label,
                taillabel=source_cardinality,
                headlabel=target_cardinality,
                tooltip=tooltip,
                color="#1E88E5",
                style="dashed",
                fontsize="10",
                labelfontsize="9",
                labeldistance="1.8",
                labelangle="25",
            )    
    # Render the graph to a file and open it
    # dot.render(output_file, view=view_diagram)           
    # output = dot.pipe(format='png')
    # output = base64.b64encode(output).decode('utf-8')
    return dot

def getDescription(cls, obj):
    print(cls, str(obj))
    if cls == 'Scale':
        return f'{obj.scale_type} scale {obj.unit.name}', url_for('main.scale', scale_id=obj.id)
    if cls == 'Conversion':
        return f'to {obj.dst_scale.scale_type} scale {obj.dst_scale.unit.name}', None
    if cls == 'Aspect':
        return str(obj), url_for('main.aspect', aspect_id=obj.id)
    if cls == 'Dimension':
        dim = ['M', 'L', 'T', 'I', greek_alphabet_unicode['Theta'], 'N', 'J']
        dimQ = ''.join([m+superscript_integers_unicode[str(n)] for m, n in zip(dim, json.loads(obj.exponents))])
        return dimQ, None 
    else:
        return str(obj), None
    

def visualize_model_instance(model, instance, excludes=[], add_labels=True, view_diagram=True):
    dot = graphviz.Digraph(comment='Interactive Data Models', format='svg', 
                            graph_attr={'bgcolor': '#EEEEEE', 'rankdir': 'TB', 'splines': 'spline'},
                            node_attr={'shape': 'none', 'fontsize': '11', 'fontname': 'Roboto'},
                            edge_attr={'fontsize': '10', 'fontname': 'Roboto'})
    
    insp = inspect(model)
    cls_name = insp.class_.__name__
    
    name, url = getDescription(cls_name, instance) 
    print(name, url) 
    # Create the node with added hyperlink to detailed documentation
    dot.node(name, label=name, URL=url) 

    # Add relationships with tooltips and advanced styling
    for rel in insp.relationships:
        
        obj = getattr(instance, rel.key)
        if obj is None:
            continue
        if isinstance(obj, list):
            if len(obj) == 0:
                continue
            target_name = f'{rel.mapper.class_.__name__} \n'
            if rel.mapper.class_.__name__ == 'KcdbCmc':
                descr, url = getDescription(rel.mapper.class_.__name__, obj[0])
                if(len(obj) > 1): 
                    target_name += f'{descr} ... \n '
                else: 
                    target_name += f'{descr} \n '
                if target_name in excludes:
                    continue
            else:
                for sub in obj:
                    descr, url = getDescription(rel.mapper.class_.__name__, sub)
                    target_name += f'{descr} \n '
                    if target_name in excludes:
                        continue
                
            tooltip = f"Relation between {name} and {target_name}"
            dot.edge(name, target_name, label=f'has {rel.key}' if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
        else:
            descr, url = getDescription(rel.mapper.class_.__name__, obj)
            target_name = f'{rel.mapper.class_.__name__} \n {descr}'
            if target_name in excludes:
                continue
            
            tooltip = f"Relation between {name} and {target_name}"
            dot.edge(name, target_name, label=f'has {rel.key}' if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
    
    # output = dot.pipe(format='png')
    # output = base64.b64encode(output).decode('utf-8')
    return dot
