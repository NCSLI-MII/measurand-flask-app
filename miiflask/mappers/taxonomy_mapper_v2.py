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
import pprint as mpprint
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
    taxon["@replacement"] = data.pop("replacement")
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

class ValidationError(Exception):
    
    def __init__(self, message="Validation error", value=None):
        self.message = message
        self.value = value
        super().__init__(self.message)


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
        self._schemas["reference"] = model.ReferenceSchema()

        self._mii_taxons_dict = {}
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
        measurand_aspect = None
        aspect = None
        result_aspect = None
        parameter = None
        # TBD need to validate existing parameters of measurand
        if "mtc:Parameter" in taxon.keys():
            # The following removes the first parameter that is generally the result
            #if len(taxon["mtc:Parameter"])>0:
            #    if (taxon["mtc:Result"]["uom:Quantity"]["@name"] != "ratio"):
            #        primary_parameter = taxon["mtc:Parameter"].pop(0)
                   
            if not isinstance(taxon["mtc:Parameter"], list): 
                taxon["mtc:Parameter"] = [taxon["mtc:Parameter"]]
            
            if "mtc:mLayer" in taxon["mtc:Parameter"][0].keys():
                measurand_aspect = (
                        self.Session.query(model.Aspect)
                        .filter((model.Aspect.id == taxon["mtc:Parameter"][0]["mtc:mLayer"]["@id"]))
                        .first()
                        )
            for parm in taxon["mtc:Parameter"]:
                try:
                    parameter = self._schemas["parameter"].load(
                            {"name": parm["@name"], 
                             "optional": parm["@optional"],
                             "definition": parm["mtc:Definition"]}, 
                            session=self.Session
                    )
                except KeyError as k:
                    print(f"{taxon['@name']} Parameter {parm['@name']} missing key {k}")
                    if k.args[0] == '@name':
                        raise KeyError
                    elif k.args[0] == '@optional':
                        raise KeyError
                    elif k.args[0] == 'mtc:Definition':
                        parameter = self._schemas["parameter"].load(
                                {"name": parm["@name"], 
                                 "optional": parm["@optional"],
                                 "definition": None}, 
                                session=self.Session
                        )
                    else:
                        raise KeyError

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
                parameter = None
                aspect = None
      
        if "mtc:mLayer" in taxon["mtc:Result"].keys():
            aspect = (
                    self.Session.query(model.Aspect)
                    .filter((model.Aspect.id == taxon["mtc:Result"]["mtc:mLayer"]["@id"]))
                    .first()
                    )
            if aspect:
                measurand.aspect = aspect
            aspect = None
            result_aspect = (
                    self.Session.query(model.Aspect)
                    .filter((model.Aspect.id == taxon["mtc:Result"]["mtc:mLayer"]["@id"]))
                    .first()
                    )
            if result_aspect:
                measurand.result_aspect = result_aspect
            result_aspect = None

        if measurand_aspect and measurand.aspect:
            if(measurand_aspect.id != measurand.aspect.id):
                print("Invalid match for measurand aspect")
                print(taxon)
                print(measurand_aspect.id, measurand_aspect.ml_name)
                print(measurand.aspect.id, measurand.aspect.ml_name)
                print(taxon["mtc:Result"]["mtc:mLayer"]["@id"])
                print(taxon["mtc:Parameter"][0]["mtc:mLayer"]["@id"])

        if "mtc:ExternalReferences" in taxon.keys():
            if not isinstance(taxon["mtc:ExternalReferences"], list): 
                taxon["mtc:ExternalReferences"] = [taxon["mtc:ExternalReferences"]]
            print(taxon["mtc:ExternalReferences"])
            for _ in taxon["mtc:ExternalReferences"]:
                ref = _["mtc:Reference"]
                print(ref)
                if "mtc:CategoryTag" in ref.keys():
                    reference = self._schemas["reference"].load(
                        {"category_name": ref["mtc:CategoryTag"]["mtc:name"],
                        "category_value": ref["mtc:CategoryTag"]["mtc:value"],
                        "reference_name": ref["mtc:ReferenceUrl"]["mtc:name"],
                        "reference_url": ref["mtc:ReferenceUrl"]["mtc:url"]},
                        session=self.Session
                        )
                else:
                    reference = self._schemas["reference"].load(
                        {"category_name": None, 
                        "category_value": None, 
                        "reference_name": ref["mtc:ReferenceUrl"]["mtc:name"],
                        "reference_url": ref["mtc:ReferenceUrl"]["mtc:url"]},
                        session=self.Session
                        )
                measurand.external_references.append(reference)

    def getMeasurandTaxonObject(self, taxon):
        """
        Deserialize taxon
        Load or create from DB
        """
        
        # Measurands can have the same taxon but differ in parameters
        # Look at rule 10
        # These are canonical definitions that contain all possible parameters
        #print(taxon)
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
            "result_quantity": taxon["mtc:Result"]["uom:Quantity"]["@name"].lower(),
            "deprecated": taxon["@deprecated"],
            "replacement": taxon["@replacement"],
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
        if(validation_errors > 0):
            raise(ValidationError)

    def loadTaxonomy(self):
        admin = model.Administrative(mii_comment=self._mii_comment)
        for taxon in self._mii_taxons_dict:
            try:
                self.getMeasurandTaxonObject(self._mii_taxons_dict[taxon])
            except KeyError as k:
                print(f'{taxon} missing key {k.args[0]}')
            except Exception as e:
                raise e

    def extractTaxonomy_v2(self):
        if isinstance(self._path, Path):
            with self._path.open() as f:
                mii_dict = xmltodict.parse(f.read(), process_comments=True)
        else:
            webf = urllib.request.urlopen(self._path, process_comments=True)
            mii_dict = xmltodict.parse(webf.read())
        
        self._mii_comment = mii_dict['#comment']
        for taxon in mii_dict["mtc:Taxonomy"]["mtc:Taxon"]:
            self._mii_taxons_dict[taxon["@name"]] = taxon


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
    def _dicttoxml_taxon(self, taxon):
        taxon["@xmlns:uom"] = "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/UOM_Database"
        taxon["@xmlns:mtc"] = "https://cls-schemas.s3.us-west-1.amazonaws.com/MII/MeasurandTaxonomyCatalog"
        _taxon = {"mtc:Taxon": taxon}
        xml = xmltodict.unparse(_taxon, pretty=True)
        return xml
    
    @classmethod
    def _getTaxonDict(self, obj, schema):
        # The dictionary is used to serialize to XML using xmltodict
        # The order of the dictionary elements must conform to the schema
        # 

        #mpprint(self._schemas["measurand"].dumps(obj, indent=2))
        #data = self._schemas["measurand"].dump(obj)
        data = schema.dump(obj)
        if "name" not in data.keys():
            return None

        taxon = {}
        
        taxon["@name"] = data.pop("name")
        taxon["@deprecated"] = data.pop("deprecated")
        taxon["@deprecated"] = "true" if taxon["@deprecated"] is True else "false" 
        taxon["@replacement"] = data.pop("replacement")
        
        # Include external references if available
        if "external_references" in data.keys():
            if len(data["external_references"]) > 0:
                taxon["mtc:ExternalReferences"] = []
                for ref in data["external_references"]:
                    dict_ = {}
                    dict_["mtc:Reference"] = {
                            "mtc:CategoryTag": {
                                "mtc:name": ref["category_name"],
                                "mtc:value": ref["category_value"]
                                },
                            "mtc:ReferenceUrl": {
                                "mtc:name": ref["reference_name"],
                                "mtc:url": ref["reference_url"]
                                }
                            }
                    taxon["mtc:ExternalReferences"].append(dict_)
                if len(taxon["mtc:ExternalReferences"]) == 1:
                    taxon["mtc:ExternalReferences"] = taxon["mtc:ExternalReferences"][0] 
        
        # Include the result
        taxon["mtc:Result"] = {"@name": data.pop("result","")}
       
        # Add uom:Quantity to Result if exists
        if 'quantitykind' in data.keys():
            if data['quantitykind']:
                taxon["mtc:Result"]["uom:Quantity"] = {
                        "@name": data['quantitykind']
                        }
        
        # Add aspect to Result         
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

        # Add parameters to taxon
        if "parameters" in data.keys():
            if len(data["parameters"]) > 0:
                taxon["mtc:Parameter"] = []
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
        
        # Add disciple to taxon
        if data['discipline']:
            taxon["mtc:Discipline"] = {
                "@name": data["discipline"]['label']
            }
        else:
            taxon["mtc:Discipline"] = {
                "@name": "" 
            }

        # Add definition
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
