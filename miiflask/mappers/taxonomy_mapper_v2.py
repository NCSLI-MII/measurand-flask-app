#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""

"""
from pathlib import Path
from unittest import TestCase
import urllib
import re
import string
import xmltodict, xmlschema
from marshmallow import pprint as mpprint
from miiflask.flask import model

import pandas as pd

def dicttoxml_taxonomy(taxons):
    taxonomy = {
        "mtc:Taxonomy": {
            "@xmlns:uom": "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/UOM_Database",
            "@xmlns:mtc": "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/MeasurandTaxonomyCatalog",
            "mtc:Taxon": taxons
        
        }
    }
    xml = xmltodict.unparse(taxonomy, pretty=True)

    return xml


def getTaxonDict_deprecated(obj, schema):
    # Old data model using Measurand and Taxon
    #mpprint(self._schemas["measurand"].dumps(obj, indent=2))
    #data = self._schemas["measurand"].dump(obj)
    data = schema.dump(obj)
    print(data)
    if "name" not in data.keys():
        return None

    taxon = {}
    #taxon["mtc:Taxon"] = {}
    taxon["@name"] = data.pop("name")
    taxon["@deprecated"] = data['taxon'].pop("deprecated")
    taxon["@replacement"] = ""
    taxon["mtc:Definition"] = data.pop("definition", "")
    taxon["mtc:Discipline"] = {
        "@name": data.pop("discipline", "")
    }
    taxon["mtc:ExternalReference"] = {
        "@name": data.pop("exref_name", ""),
        "mtc:url": data.pop("exref_url", ""),
    }
    taxon["mtc:Parameter"] = []
    if "parameters" in data.keys():
        for parm in data["parameters"]:
            if parm["name"] == "id":
                continue
            if parm["name"] == "measurand":
                continue
            taxon["mtc:Parameter"].append(
                {
                    "@name": parm["name"],
                    "@optional": parm["optional"],
                    "mtc:Definition": parm["definition"],
                    "uom:Quantity": {"@name": parm["quantitykind"]}
                },

            )
    taxon["mtc:Result"] = {
        "@name": data.pop("result", ""),
        "uom:Quantity": {"@name": data.pop("quantitykind", "")},
    }

    print(data)
    #print(xmltodict.unparse(taxon))
    return taxon

def getTaxonDict(obj, schema):
    #mpprint(self._schemas["measurand"].dumps(obj, indent=2))
    #data = self._schemas["measurand"].dump(obj)
    data = schema.dump(obj)
    
    if "name" not in data.keys():
        return None

    taxon = {}
    #taxon["mtc:Taxon"] = {}
    taxon["@name"] = data.pop("name")
    taxon["@deprecated"] = data.pop("deprecated")
    taxon["@replacement"] = ""
    taxon["mtc:Definition"] = data.pop("definition", "")
    if data['discipline']:
        taxon["mtc:Discipline"] = {
            "@name": data["discipline"]['label']
        }
    else:
        taxon["mtc:Discipline"] = {
            "@name": "" 
        }

    taxon["mtc:ExternalReference"] = {
        "@name": data.pop("exref_name", ""),
        "mtc:url": data.pop("exref_url", ""),
    }
    taxon["mtc:Parameter"] = []
    if "parameters" in data.keys():
        for parm in data["parameters"]:
            if parm["name"] == "id":
                continue
            if parm["name"] == "measurand":
                continue
            if parm['aspect']:
                taxon["mtc:Parameter"].append(
                    {
                        "@name": parm["name"],
                        "@optional": parm["optional"],
                        "mtc:Definition": parm["definition"],
                        "uom:Quantity": {"@name": parm["quantitykind"]},
                        "mtc:Aspect":{
                                "@name": parm['aspect']['name'],
                                "@id": parm['aspect']['id']
                                }
                    },
                    )
            else:
                taxon["mtc:Parameter"].append(
                    {
                        "@name": parm["name"],
                        "@optional": parm["optional"],
                        "mtc:Definition": parm["definition"],
                        "uom:Quantity": {"@name": parm["quantitykind"]},
                        "mtc:Aspect":{
                                "@name": "", 
                                "@id": "" 
                                }
                    },
                )
    taxon["mtc:Result"] = {
        "@name": data.pop("result", ""),
        "uom:Quantity": {"@name": data.pop("quantitykind", "")},
    }
    if 'aspect' in data.keys():
        if data['aspect']:
            taxon["mtc:Aspect"] = {
                    "@name": data['aspect']['name'],
                    "@id": data['aspect']['id']
                    }
    if 'scale' in data.keys(): 
        if data['scale']:
            taxon["mtc:Scale"] = {
                    "@name": data['scale']['ml_name'],
                    "@id": data['scale']['id']
                    }

    #print(data)
    #print(xmltodict.unparse(taxon))
    return taxon


class TaxonomyMapper:
    """
    Parses/Unparses MII Taxonomy data
    Serializes/Deserializes Taxons with ORM Measurand model

    Purpose is to round trip XML hierachercal representation and SQL relational data
    Taxons can either be defined via ORM/DB application or XML hierarchical

    UOM DB is replaced by MLayer defined quantities

    """

    def __init__(self, session, parms):
        if 'resources' in parms['measurands']:
            self._path = Path(parms["measurands"]).resolve()
        else:
            self._path = parms['measurands']
        self._schema_taxonomy = "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/MeasurandTaxonomyCatalog"
        if "taxonomy_xml" in parms.keys():
            self._taxonomy_xml = Path(parms["taxonomy_xml"]).resolve()
        else:
            self._taxonomy_xml = None

        self._schema_uom = (
            "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/UOM_Database"
        )

        self._namespaces = {
            "mtc": f"{self._schema_taxonomy}:Taxonomy",
            "uom": f"{self._schema_uom}:uom",
            "quantity": f"{self._schema_uom}:Quantity",
            "taxon": f"{self._schema_taxonomy}:Taxon",
            "exref": f"{self._schema_taxonomy}:ExternalReference",
            "discipline": f"{self._schema_taxonomy}:Discipline",
            "url": f"{self._schema_taxonomy}:url",
            "definition": f"{self._schema_taxonomy}:Definition",
            "result": f"{self._schema_taxonomy}:Result",
            "parameter": f"{self._schema_taxonomy}:Parameter",
            "mlayer": f"{self._schema_taxonomy}:mLayer",
        }
        self._schemas = {}
        self._schemas["taxon"] = model.TaxonSchema()
        self._schemas["aspect"] = model.AspectSchema()
        self._schemas["discipline"] = model.DisciplineSchema()
        self._schemas["measurand"] = model.MeasurandSchema()
        self._schemas["measurandtaxon"] = model.MeasurandTaxonSchema()
        self._schemas["parameter"] = model.ParameterSchema()

        self._mii_taxons_dict = None
        self._mii_taxons_list = None
        self._mii_comment = None
        self.Session = session

    def xml_template(self, **kwargs):
        """
        kwargs:
        reference
        result
        parameters
        discipline
        definition
        """
        if "name" not in kwargs.keys():
            return None

        taxon = {}
        taxon["mtc:Taxon"] = {}
        taxon["mtc:Taxon"]["@name"] = kwargs.pop("name")
        taxon["mtc:Taxon"]["@deprecated"] = "false"
        taxon["mtc:Taxon"]["@replacement"] = ""
        taxon["mtc:Taxon"]["mtc:Definition"] = kwargs.pop("definition", "")
        taxon["mtc:Taxon"]["mtc:Discipline"] = {
            "@name": kwargs.pop("discipline", "")
        }
        taxon["mtc:Taxon"]["mtc:ExternalReference"] = {
            "@name": kwargs.pop("exref_name", ""),
            "mtc:url": kwargs.pop("exref_url", ""),
        }
        taxon["mtc:Taxon"]["mtc:Parameter"] = []
        if "parameters" in kwargs.keys():
            for parm in kwargs["parameters"]:
                taxon["mtc:Taxon"]["mtc:Parameter"].append(
                    {"@name": parm, "@optional": "false", "@uom:Quantity": ""}
                )
        taxon["mtc:Taxon"]["mtc:Result"] = {
            "@name": kwargs.pop("result", ""),
            "uom:Quantity": {"@name": kwargs.pop("uom", "")},
        }

        # pprint(xmltodict.unparse(taxon))
        return taxon["mtc:Taxon"]

    #def _transformQuantityName(self, obj):

    def _associateAspect(self, obj):
        if obj.quantitykind:
            # Conform to UOM:Quantity name conventions for matching
            # Leave mtc:Parameter in place 
            # name_ = obj.quantitykind 
            # name_ = name_.rstrip()
            # name_ - name_.lower().replace(" ", "-")
            try:
                aspect = (
                        self.Session.query(model.Aspect)
                        .filter(model.Aspect.name == obj.quantitykind.lower()) 
                        .first()
                        )
            except Exception as ex:
                print(ex)
                print(f"Object name:{obj.name}, Object QuantityKind:{obj.quantitykind}, Transformed QuantityKind Name:{name_}")
                aspect = None
            if aspect:
                obj.aspect = aspect
            else:
                name_ = obj.quantitykind.lower()
                if name_ == "ratio":
                    aspect = None
                #print(f"Cannot match {obj.name} try like {name_}")
                else:
                    aspect = (
                            self.Session.query(model.Aspect)
                            .filter((model.Aspect.name.like(f'%{name_}%')))
                            .first()
                            )
                # Ratio quantity ignored
                # Needs to further specified for relating to an aspect
                if aspect:
                    obj.aspect = aspect
                    #print(f"Found corresponding aspect {aspect.name} for {obj.name} with quantitykind {name_}")


    def getMeasurandRelatedObjects(self, taxon, measurand, uom_qk=None):
        if uom_qk:
            measurand.quantitykind = uom_qk 
        
        # First required parameter which represents the quantity kind or aspect
        # validate against the aspect
        primary_parameter = None
        # TBD need to validate existing parameters of measurand
        if "mtc:Parameter" in taxon.keys():
            # The following removes the first parameter that is generally the result
            #if len(taxon["mtc:Parameter"])>0:
            #    if (taxon["mtc:Result"]["uom:Quantity"]["@name"] != "ratio"):
            #        primary_parameter = taxon["mtc:Parameter"].pop(0)
                   
            for parm in taxon["mtc:Parameter"]:
                
                parameter = self._schemas["parameter"].load(
                        {"name": parm["@name"], 
                         "optional": parm["@optional"],
                         "definition": parm["mtc:Definition"]}, 
                        session=self.Session
                )
                if "uom:Quantity" in parm.keys():
                    parameter.quantitykind = parm["uom:Quantity"]["@name"]
                if "mtc:mLayer" in parm.keys():
                    aspect = (
                            self.Session.query(model.Aspect)
                            .filter((model.Aspect.id == parm["mtc:mLayer"]["@id"]))
                            .first()
                            )
                    if aspect:
                        parameter.aspect = aspect
                measurand.parameters.append(parameter)
      
        if "mtc:mLayer" in taxon["mtc:Result"].keys():
            aspect = (
                    self.Session.query(model.Aspect)
                    .filter((model.Aspect.id == taxon["mtc:Result"]["mtc:mLayer"]["@id"]))
                    .first()
                    )
            if aspect:
                measurand.aspect = aspect
   

    def _preprocessTaxon(self, taxon):
        if "mtc:Parameter" in taxon.keys():
            # Conform to XML Schema Name
            # Conform to UOM Name conventions
            # Quantity names must start with a lower case letter, contain only lower case letters, hyphens (-) or colons (:)
            for i, parm in enumerate(taxon["mtc:Parameter"]):
                # Remove trailing whitespace
                taxon["mtc:Parameter"][i]["@name"] = taxon["mtc:Parameter"][i]["@name"].rstrip()
                # Replace underscore with -
                taxon["mtc:Parameter"][i]["@name"] = taxon["mtc:Parameter"][i]["@name"].replace("_",".")
                # Capitalize each word
                taxon["mtc:Parameter"][i]["@name"] = re.sub(r'\b[a-z]',lambda m: m.group().upper(),taxon["mtc:Parameter"][i]["@name"])
                # Remove whitespace
                taxon["mtc:Parameter"][i]["@name"] = taxon["mtc:Parameter"][i]["@name"].replace(" ", "")
                # Change Captitalization to space
                # taxon["mtc:Parameter"][i]["@name"] = re.sub(r"([a-z])(?=[A-Z])|[A-Z](?=[A-Z][a-z])", r"\1 ", taxon["mtc:Parameter"][i]["@name"])
                # Drop to lower, change whitespace to -
                # taxon["mtc:Parameter"][i]["@name"] = taxon["mtc:Parameter"][i]["@name"].lower().replace(" ","-")
                # change . to -
                # taxon["mtc:Parameter"][i]["@name"] = taxon["mtc:Parameter"][i]["@name"].lower().replace(".","-")
            
        return taxon

    def getMeasurandTaxonObject(self, taxon):
        """
        Deserialize taxon
        Load or create from DB
        """
        
        # Measurands can have the same taxon but differ in parameters
        # Look at rule 10
        # These are canonical definitions that contain all possible parameters

        discipline_data = {"label": taxon["mtc:Discipline"]["@name"]}
        
        # TBD
        # id and name of taxon should follow
        # BNF grammar
        # Flask problems with formatting url with taxon name
        id_ = taxon["@name"].replace('.', '')
        # -----------------------------------
        # Following updates Parameter names to conform to UOM:Quantity Name
        # Quantity names must start with a lower case letter, contain only lower case letters, hyphens (-) or colons (:)
        # Should no longer be required, all formatting issues resolved
        # taxon = self._preprocessTaxon(taxon)
        # ------------------------------------
        taxon_data = {
            "id": id_,
            "name": taxon["@name"],
            "definition": taxon['mtc:Definition'],
            "processtype": taxon["@name"].split(".")[0],
            "quantitykind": taxon["mtc:Result"]["uom:Quantity"]["@name"].lower(),
            "deprecated": taxon["@deprecated"],
            "result": taxon["mtc:Result"]["@name"]
        }

        discipline = (
            self.Session.query(model.Discipline)
            .filter(model.Discipline.label == discipline_data["label"])
            .first()
        )
        if not discipline:
            discipline = self._schemas["discipline"].load(
                discipline_data, session=self.Session
            )
            self.Session.add(discipline)

        taxon_ = (
            self.Session.query(model.MeasurandTaxon)
            .filter(model.MeasurandTaxon.name == taxon_data["name"])
            .first()
        )
        if not taxon_:
            taxon_ = self._schemas["measurandtaxon"].load(
                taxon_data, session=self.Session
            )
            taxon_.discipline = discipline
            # taxon_.quantitykind = quantitykind
            self.Session.add(taxon_)
            self.getMeasurandRelatedObjects(taxon, taxon_) 
    
    def roundtrip(self):
        # Compare taxonomy dictionary after ETL
        if isinstance(self._path, Path):
            with self._path.open() as f:
                mii_dict = xmltodict.parse(
                    f.read() 
                )
        else:
            webf = urllib.request.urlopen(self._path)
            mii_dict = xmltodict.parse(webf.read())

        #print(mii_dict['mtc:Taxonomy']['mtc:Taxon'][0])
        validation_errors = 0
        for taxon in mii_dict['mtc:Taxonomy']['mtc:Taxon']:
            obj = (
                self.Session.query(model.MeasurandTaxon)
                .filter(model.MeasurandTaxon.name == taxon["@name"])
                .first()
            )
            if obj:
                dict_ = self._getTaxonDict(obj, self._schemas["measurandtaxon"])
            case = TestCase()
            case.maxDiff = None
            try:
                case.assertDictEqual(dict(taxon), dict_)
            except Exception as e:
                print("Expected from source")
                print(dict(taxon))
                print("================")
                print("Serialized from DB")
                print(dict_)
                print("================")
                print(e)
                validation_errors += 1

        print("Total validation errors: ", validation_errors)






    def loadTaxonomy(self):
        admin = model.Administrative(mii_comment=self._mii_comment)
        for taxon in self._mii_taxons_dict:
            self.getMeasurandTaxonObject(self._mii_taxons_dict[taxon])

    def extractTaxonomy(self):
        if isinstance(self._path, Path):
            with self._path.open() as f:
                mii_dict = xmltodict.parse(
                    f.read(), process_namespaces=True, process_comments=True,namespaces=self._namespaces
                )
        else:
            webf = urllib.request.urlopen(self._path)
            mii_dict = xmltodict.parse(webf.read(), process_namespaces=True, process_comments=True, namespaces=self._namespaces)


        mii_taxons_dict = {}
        mii_taxons_flat = []
        # Populate QuantityKind Table
        print(mii_dict.keys())
        print(mii_dict['#comment'])
        self._mii_comment = mii_dict['#comment']
        for taxon in mii_dict[self._namespaces["mtc"]][
            self._namespaces["taxon"]
        ]:
            #print(taxon)
            if taxon["@name"].split(".")[0] == "TestProcess":
                taxon["@name"] = ".".join(taxon["@name"].split(".")[1:])
            mii_taxons_dict[taxon["@name"]] = {
                "@name": taxon["@name"],
                "@deprecated": taxon["@deprecated"],
                "@replacement": taxon["@replacement"],
                "mtc:Definition": taxon[self._namespaces["definition"]],
                "mtc:Discipline": {
                    "@name": taxon[self._namespaces["discipline"]]["@name"]
                },
                "mtc:Result": {
                    "@name": taxon[self._namespaces["result"]]["@name"],
                    "uom:Quantity": {
                        "@name": taxon[self._namespaces["result"]][
                            self._namespaces["quantity"]
                        ]["@name"]
                    },
                }
            }
            if self._namespaces["mlayer"] in taxon[self._namespaces["result"]].keys():
                mii_taxons_dict[taxon["@name"]]["mtc:Result"]["mtc:mLayer"] = { 
                            "@aspect": taxon[self._namespaces["result"]][
                                self._namespaces["mlayer"]
                            ]["@aspect"],
                            "@id": taxon[self._namespaces["result"]][
                                self._namespaces["mlayer"]
                            ]["@id"]
                        }

            if self._namespaces["parameter"] in taxon.keys():
                mii_taxons_dict[taxon["@name"]]["mtc:Parameter"] = []
                if type(taxon[self._namespaces["parameter"]]) is dict:
                    parm = taxon[self._namespaces["parameter"]]
                    _dict = {
                        "@name": parm["@name"],
                        "@optional": parm["@optional"],
                        "uom:Quantity": {
                            "@name": parm[self._namespaces["quantity"]][
                                "@name"
                            ],
                        },
                        "mtc:Definition": parm[self._namespaces["definition"]],
                    }
                    if self._namespaces["mlayer"] in parm.keys():
                        _dict["mtc:mLayer"] = { 
                                    "@aspect": parm[self._namespaces["mlayer"]][
                                        "@aspect"
                                    ],
                                    "@id": parm[self._namespaces["mlayer"]][
                                        "@id"
                                    ],
                                }

                    mii_taxons_dict[taxon["@name"]]["mtc:Parameter"].append(
                        _dict
                    )
                else:
                    for parm in taxon[self._namespaces["parameter"]]:
                        _dict = {}
                        # print(parm.keys())
                        if self._namespaces["quantity"] in parm.keys():
                            _dict = {
                                "@name": parm["@name"],
                                "@optional": parm["@optional"],
                                "uom:Quantity": {
                                    "@name": parm[
                                        self._namespaces["quantity"]
                                    ]["@name"]
                                },
                                "mtc:Definition": parm[
                                    self._namespaces["definition"]
                                ],
                            }
                            if self._namespaces["mlayer"] in parm.keys():
                                _dict["mtc:mLayer"] = { 
                                            "@aspect": parm[self._namespaces["mlayer"]][
                                                "@aspect"
                                            ],
                                            "@id": parm[self._namespaces["mlayer"]][
                                                "@id"
                                            ],
                                        }
                        else:
                            _dict = {
                                "@name": parm["@name"],
                                "@optional": parm["@optional"],
                                "mtc:Definition": parm[
                                    self._namespaces["definition"]
                                ]
                            }
                        mii_taxons_dict[taxon["@name"]][
                            "mtc:Parameter"
                        ].append(_dict)
            mii_taxons_flat.append(mii_taxons_dict[taxon["@name"]])

        self._mii_taxons_dict = mii_taxons_dict
        self._mii_taxons_list = mii_taxons_flat

    def flattenTaxonomy(self):
        # DEPRECATED
        # Set tables path if needed
        rows = list()
        for taxon in self._mii_taxons_dict:
            row = [self._mii_taxons_dict[taxon]["@name"]]
            row.append(self._mii_taxons_dict[taxon]["mtc:Discipline"]["@name"])
            parms = list()
            if "mtc:Parameter" in self._mii_taxons_dict[taxon].keys():
                for parm in self._mii_taxons_dict[taxon]["mtc:Parameter"]:
                    parms.append(parm["@name"])
            row.append("[" + ",".join(str(x) for x in parms) + "]")
            rows.append(row)
        df = pd.DataFrame(rows)
        df.columns = ["Taxon", "Discipline", "Quantities"]
        with pd.ExcelWriter(self._tables) as writer:
            for k, tmpdf in df.groupby("Discipline"):
                if k == "Acoustics, ultrasound and vibration":
                    name = "AUV"
                else:
                    name = k
                tmpdf.to_excel(writer, sheet_name=name, index=False)

    @classmethod
    def _dicttoxml_taxonomy(self, taxons):
        taxonomy = {
            "mtc:Taxonomy": {
                "@xmlns:uom": "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/UOM_Database",
                "@xmlns:mtc": "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/MeasurandTaxonomyCatalog",
                "mtc:Taxon": taxons
            
            }
        }
        xml = xmltodict.unparse(taxonomy, pretty=True)

        return xml
    
    @classmethod
    def _getTaxonDict(self, obj, schema):
        #mpprint(self._schemas["measurand"].dumps(obj, indent=2))
        #data = self._schemas["measurand"].dump(obj)
        data = schema.dump(obj)
        if "name" not in data.keys():
            return None

        taxon = {}
        
        taxon["@name"] = data.pop("name")
        taxon["@deprecated"] = data.pop("deprecated")
        taxon["@deprecated"] = "true" if taxon["@deprecated"] is True else "false" 
        taxon["@replacement"] = ""
        # taxon["mtc:ExternalReferences"] = []
        taxon["mtc:Result"] = {"@name": data.pop("result",""),
            "uom:Quantity": {"@name": data.pop("quantitykind", "")}
        }
        if 'aspect' in data.keys():
            if data['aspect']:
                taxon["mtc:Result"]["mtc:mLayer"] = {
                        "@aspect": data['aspect']['ml_name'],
                        "@id": data['aspect']['id']
                        }
        if 'scale' in data.keys(): 
            if data['scale']:
                taxon["mtc:Scale"] = {
                        "@name": data['scale']['ml_name'],
                        "@id": data['scale']['id']
                        }

        taxon["mtc:Parameter"] = []
        if "parameters" in data.keys():
            for parm in data["parameters"]:
                dict_ = {}
                if parm["name"] == "id":
                    continue
                if parm["name"] == "measurand":
                    continue
                dict_ = {"@name": parm["name"],
                        "@optional": "true" if parm["optional"] is True else "false",
                        "mtc:Definition": parm["definition"],
                        }
                if parm['quantitykind']:
                    dict_["uom:Quantity"] = {"@name": parm["quantitykind"]}
                if parm['aspect']:
                        dict_["mtc:mLayer"] = {
                                "@aspect": parm['aspect']['ml_name'],
                                "@id": parm['aspect']['id']
                                }
                
                taxon["mtc:Parameter"].append(dict_)
            if len(taxon["mtc:Parameter"]) == 1:
                taxon["mtc:Parameter"] = taxon["mtc:Parameter"][0]

                    

        
        if data['discipline']:
            taxon["mtc:Discipline"] = {
                "@name": data["discipline"]['label']
            }
        else:
            taxon["mtc:Discipline"] = {
                "@name": "" 
            }
        taxon["mtc:Definition"] = data.pop("definition", "")
        return taxon
    
    def _get_validation_errors(self, xml_file):
        try:
            schema = xmlschema.XMLSchema(self._schema_taxonomy+'.xsd')
        except Exception as e:
            print(e)
            raise e
        schema.validate(xml_file)
        validation_error_iterator = schema.iter_errors(xml_file)
        errors = list()
        for idx, validation_error in enumerate(validation_error_iterator, start=1):
            err = validation_error.__str__()
            print(f'sourceline: {validation_error.sourceline}; path: {validation_error.path} | reason: {validation_error.reason} | message: {validation_error.message}')
            errors.append(err)
        return errors
        
    def toXml(self):
        measurands = self.Session.query(model.MeasurandTaxon).all()
        admin = self.Session.query(model.Administrative).first()
        taxons = []
        for obj in measurands:
            try:
                taxons.append(self._getTaxonDict(obj, self._schemas["measurandtaxon"]))
            except Exception as e:
                print(obj)
                raise e
        xml = self._dicttoxml_taxonomy(taxons, admin.mii_comment)
        print(f"Write temp taxonomy file at {self._taxonomy_xml}")
        with open(self._taxonomy_xml, "w") as f:
            f.write(xml)
        self._get_validation_errors(self._taxonomy_xml)
