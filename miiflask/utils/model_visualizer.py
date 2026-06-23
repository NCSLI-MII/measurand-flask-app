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
from decimal import Decimal
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Integer, Numeric, Boolean, JSON, ForeignKey, LargeBinary, Text, UniqueConstraint, CheckConstraint, text as sql_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import inspect
import graphviz
import os
import re
import base64
import json
from flask import url_for

from miiflask.utils.unicode_mapper import greek_alphabet_unicode, superscript_integers_unicode

Base = declarative_base()


def generate_data_model_diagram(models, excludes=[], show_attributes=True, add_labels=True, view_diagram=True):
    # Initialize graph with more advanced visual settings
    dot = graphviz.Digraph(comment='Interactive Data Models', format='svg', 
                            graph_attr={'bgcolor': '#EEEEEE', 'rankdir': 'TB', 'splines': 'spline'},
                            node_attr={'shape': 'none', 'fontsize': '12', 'fontname': 'Roboto'},
                            edge_attr={'fontsize': '10', 'fontname': 'Roboto'})
    # Iterate through each SQLAlchemy model
    for model in models:
        insp = inspect(model)
        name = insp.class_.__name__

        # Create an HTML-like label for each model as a rich table
        label = f'''<
        <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
        '''
        if show_attributes is True:         
            label += f'''
            <TR>
            <TD COLSPAN="3" BGCOLOR="#3F51B5">
            <FONT COLOR="white"><B>{name}</B></FONT>
            </TD>
            </TR>

            <TR>
            <TD BGCOLOR="#E8EAF6"><B>Attribute</B></TD>
            <TD BGCOLOR="#E8EAF6"><B>Key</B></TD>
            <TD BGCOLOR="#E8EAF6"><B>Description</B></TD>
            </TR>
            '''
 
            for column in insp.columns:
                comment = column.comment or ""
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
                <TD ALIGN="LEFT" WIDTH="60" BGCOLOR="{color}">{column.name}</TD>
                <TD ALIGN="LEFT" WIDTH="40" BGCOLOR="{color}">{constraint_str}</TD>
                <TD ALIGN="LEFT" WIDTH="300">{comment}</TD>
                </TR>'''
        else:
            label += f'''<TR>
            <TD WIDTH="100" HEIGHT="50" BGCOLOR="#3F51B5"><FONT COLOR="white">{name}</FONT></TD></TR>
            '''


        label += '</TABLE>>'
        
        dot.node(name, label=label)

        # Add relationships with tooltips and advanced styling
        for rel in insp.relationships:
            target_name = rel.mapper.class_.__name__
            if target_name in excludes:
                continue
            tooltip = f"Relation between {name} and {target_name}"
            dot.edge(name, target_name, label=rel.key if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")

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
