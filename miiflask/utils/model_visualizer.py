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
Base = declarative_base()

def generate_data_model_diagram(models, excludes=[], add_labels=True, view_diagram=True):
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
        
        label += '</TABLE>>'
        
        # Create the node with added hyperlink to detailed documentation
        dot.node(name, label=label)

        # Add relationships with tooltips and advanced styling
        for rel in insp.relationships:
            target_name = rel.mapper.class_.__name__
            print(target_name)
            if target_name in excludes:
                continue
            tooltip = f"Relation between {name} and {target_name}"
            print(tooltip)
            dot.edge(name, target_name, label=rel.key if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")

    # Render the graph to a file and open it
    # dot.render(output_file, view=view_diagram)           
    output = dot.pipe(format='png')
    output = base64.b64encode(output).decode('utf-8')
    return output


def visualize_scale(scale, add_labels=True, view_diagram=True):
    dot = graphviz.Digraph(comment='Interactive Data Models', format='svg', 
                            graph_attr={'bgcolor': '#EEEEEE', 'rankdir': 'TB', 'splines': 'spline'},
                            node_attr={'shape': 'none', 'fontsize': '12', 'fontname': 'Roboto'},
                            edge_attr={'fontsize': '10', 'fontname': 'Roboto'})
    name = scale.ml_name 
    # Create an HTML-like label for each model as a rich table
    label = f'''<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
    <TR><TD COLSPAN="2" BGCOLOR="#3F51B5"><FONT COLOR="white">{name}</FONT></TD></TR>
    </TABLE>
    '''
    # Create the node with added hyperlink to detailed documentation
    dot.node(name, label=name, URL=f"http://{name}_details.html")
    # Add relationships with tooltips and advanced styling
    target_name = scale.unit.name 
    tooltip = f"Relation between {name} and {target_name}"
    dot.edge(name, target_name, label="has unit" if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")
    # Render the graph to a file and open it

    for cnv in scale.conversions:
        target_name = cnv.dst_scale.ml_name
        tooltip = f"Relation between {name} and {target_name}"
        dot.edge(name, target_name, label="converts to" if add_labels else None, tooltip=tooltip, color="#1E88E5", style="dashed")

    dot.render("test_visual_scale.png", view=view_diagram)     
    output = dot.pipe(format='png')
    output = base64.b64encode(output).decode('utf-8')
    return output
