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
        <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
        '''
        if show_attributes is True:         
            label += f'''
            <TR><TD COLSPAN="2" BGCOLOR="#3F51B5"><FONT COLOR="white">{name}</FONT></TD></TR>
            '''
       
            for column in insp.columns:
                constraints = []
                if column.primary_key:
                    constraints.append("PK")
                if column.unique:
                    constraints.append("Unique")
                if column.index:
                    constraints.append("Index")
                
                constraint_str = ','.join(constraints)
                color = "#BBDEFB"
                
                label += f'''<TR>
                             <TD BGCOLOR="{color}">{column.name} ({constraint_str})</TD>
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
    output = dot.pipe(format='png')
    output = base64.b64encode(output).decode('utf-8')
    return output

def getDescription(cls, obj):
    print(cls, str(obj))
    if cls == 'Scale':
        return f'{obj.scale_type} scale {obj.unit.name}'
    if cls == 'Conversion':
        return f'to {obj.dst_scale.scale_type} scale {obj.dst_scale.unit.name}'
    if cls == 'Aspect':
        return str(obj)
    if cls == 'Dimension':
        superscript = {'0': u'\u2070',
                       '1': u'\u00B9',
                       '2': u'\u00B2',
                       '3': u'\u00B3',
                       '4': u'\u2074',
                       '5': u'\u2075',
                       '6': u'\u2076',
                       '7': u'\u2077',
                       '8': u'\u2078',
                       '9': u'\u2079',
                       '-1': u'\u207B\u00B9',
                       '-2': u'\u207B\u00B2',
                       '-3': u'\u207B\u00B3',
                       '-4': u'\u207B\u2074',
                       '-5': u'\u207B\u2075',
                       '-6': u'\u207B\u2076',
                       '-7': u'\u207B\u2077',
                       '-8': u'\u207B\u2078',
                       '-9': u'\u207B\u2079',
                       }
        dim = ['M', 'L', 'T', 'I', u'\u0398', 'N', 'J']
        dimQ = ''.join([m+superscript[str(n)] for m, n in zip(dim, json.loads(obj.exponents))])
        return dimQ 
    else:
        return str(obj)
    

def visualize_model_instance(model, instance, excludes=[], add_labels=True, view_diagram=True):
    dot = graphviz.Digraph(comment='Interactive Data Models', format='svg', 
                            graph_attr={'bgcolor': '#EEEEEE', 'rankdir': 'TB', 'splines': 'spline'},
                            node_attr={'shape': 'none', 'fontsize': '11', 'fontname': 'Roboto'},
                            edge_attr={'fontsize': '10', 'fontname': 'Roboto'})
    
    insp = inspect(model)
    cls_name = insp.class_.__name__
    
    name = getDescription(cls_name, instance) 
    
    # Create the node with added hyperlink to detailed documentation
    dot.node(name, label=name) 

    # Add relationships with tooltips and advanced styling
    for rel in insp.relationships:
        
        obj = getattr(instance, rel.key)
        if obj is None:
            continue
        if isinstance(obj, list):
            for sub in obj:
                # print(rel.mapper.class_.__name__, sub)
                descr = getDescription(rel.mapper.class_.__name__, sub)
                # print(descr)
                target_name = f'{rel.mapper.class_.__name__} {descr}'
                if target_name in excludes:
                    continue
                
                tooltip = f"Relation between {name} and {target_name}"
                dot.edge(name, target_name, label=f'has {rel.key}' if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
        else:
            descr = getDescription(rel.mapper.class_.__name__, obj)
            target_name = f'{rel.mapper.class_.__name__} {descr}'
            if target_name in excludes:
                continue
            
            tooltip = f"Relation between {name} and {target_name}"
            dot.edge(name, target_name, label=f'has {rel.key}' if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
    
    output = dot.pipe(format='png')
    output = base64.b64encode(output).decode('utf-8')
    return output
