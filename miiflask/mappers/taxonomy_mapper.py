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
import xmltodict
from marshmallow import pprint as mpprint
from miiflask.flask import model
import pandas as pd


class TaxonomyMapper:
    """
    Parses/Unparses MII Taxonomy data
    Serializes/Deserializes Taxons with ORM Measurand model

    Purpose is to round trip XML hierachercal representation and SQL relational data
    Taxons can either be defined via ORM/DB application or XML hierarchical

    UOM DB is replaced by MLayer defined quantities

    """

    def __init__(self, session, parms):
        self._path = Path(parms["measurands"]).resolve()
        self._tables = Path(parms["usertables"]+'taxonomy').resolve()
        self._schema_taxonomy = "https://cls-schemas.s3.us-west-1.amazonaws.com/MetrologyTaxonomyCatalog"
        self._schema_uom = (
            "https://cls-schemas.s3.us-west-1.amazonaws.com/UOM_Database"
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
        }
        self._schemas = {}
        self._schemas["taxon"] = model.TaxonSchema()
        self._schemas["aspect"] = model.QuantityKindSchema()
        self._schemas["discipline"] = model.DisciplineSchema()
        self._schemas["measurand"] = model.MeasurandSchema()
        self._schemas["parameter"] = model.ParameterSchema()

        self._mii_taxons_dict = None
        self._mii_taxons_list = None
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

    def dicttoxml_taxonomy(self, taxons):
        taxonomy = {
            "mtc:Taxonomy": {
                "@xmlns:uom": "https://cls-schemas.s3.us-west-1.amazonaws.com/UOM_Database",
                "@xmlns:mtc": "https://cls-schemas.s3.us-west-1.amazonaws.com/MetrologyTaxonomyCatalog",
            }
        }
        taxonomy["mtc:Taxonomy"]["mtc:Taxon"] = taxons
        xml = xmltodict.unparse(taxonomy)

        return xml

    def getTaxonDict(self, obj):
        mpprint(self._schemas["measurand"].dumps(obj, indent=2))
        data = self._schemas["measurand"].dump(obj)

        if "name" not in data.keys():
            return None

        taxon = {}
        taxon["mtc:Taxon"] = {}
        taxon["mtc:Taxon"]["@name"] = data.pop("name")
        taxon["mtc:Taxon"]["@deprecated"] = "false"
        taxon["mtc:Taxon"]["@replacement"] = ""
        taxon["mtc:Taxon"]["mtc:Definition"] = data.pop("definition", "")
        taxon["mtc:Taxon"]["mtc:Discipline"] = {
            "@name": data.pop("discipline", "")
        }
        taxon["mtc:Taxon"]["mtc:ExternalReference"] = {
            "@name": data.pop("exref_name", ""),
            "mtc:url": data.pop("exref_url", ""),
        }
        taxon["mtc:Taxon"]["mtc:Parameter"] = []
        if "parameters" in data.keys():
            for parm in data["parameters"]:
                if parm["name"] == "id":
                    continue
                if parm["name"] == "measurand":
                    continue
                taxon["mtc:Taxon"]["mtc:Parameter"].append(
                    {
                        "@name": parm["name"],
                        "@optional": "false",
                        "@uom:Quantity": "",
                    }
                )
        taxon["mtc:Taxon"]["mtc:Result"] = {
            "@name": data.pop("result", ""),
            "uom:Quantity": {"@name": data.pop("uom", "")},
        }

        print(data)
        print(xmltodict.unparse(taxon))
        return taxon

    def getMeasurandObject(self, taxon):
        """
        Deserialize taxon
        Load or create from DB
        """
        # print(taxon)
        quantitykind_data = {
            "name": taxon["mtc:Result"]["uom:Quantity"]["@name"]
        }
        discipline_data = {"label": taxon["mtc:Discipline"]["@name"]}
        taxon_data = {
            "name": taxon["@name"],
            "process": taxon["@name"].split(".")[0],
        }

        # Measurands can have the same taxon but differ in parameters
        # Look at rule 10
        measurand_data = {"name": taxon["@name"]}

        quantitykind = (
            self.Session.query(model.QuantityKind)
            .filter(model.QuantityKind.name == quantitykind_data["name"])
            .first()
        )
        if not quantitykind:
            quantitykind = self._schemas["aspect"].load(
                quantitykind_data, session=self.Session
            )
            self.Session.add(quantitykind)

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
            self.Session.query(model.Taxon)
            .filter(model.Taxon.name == taxon_data["name"])
            .first()
        )
        if not taxon_:
            taxon_ = self._schemas["taxon"].load(
                taxon_data, session=self.Session
            )
            taxon_.discipline = discipline
            taxon_.quantitykind = quantitykind
            self.Session.add(taxon_)

        measurand = (
            self.Session.query(model.Measurand)
            .filter(model.Measurand.name == measurand_data["name"])
            .first()
        )
        if not measurand:
            measurand = self._schemas["measurand"].load(
                measurand_data, session=self.Session
            )
            measurand.taxon = taxon_
            measurand.quantitykind = quantitykind
            self.Session.add(measurand)

            # TBD need to validate existing parameters of measurand
            if "mtc:Parameter" in taxon.keys():
                for parm in taxon["mtc:Parameter"]:
                    parameter = self._schemas["parameter"].load(
                        {"name": parm["@name"]}, session=self.Session
                    )
                    if "uom:Quantity" in parm.keys():
                        parm_qk_data = {"name": parm["uom:Quantity"]["@name"]}
                        parm_quantitykind = (
                            self.Session.query(model.QuantityKind)
                            .filter(
                                model.QuantityKind.name == parm_qk_data["name"]
                            )
                            .first()
                        )
                        if not parm_quantitykind:
                            parm_quantitykind = self._schemas["aspect"].load(
                                parm_qk_data, session=self.Session
                            )
                            self.Session.add(parm_quantitykind)
                            print(parm_qk_data)
                        parameter.quantitykind = parm_quantitykind
                    measurand.parameters.append(parameter)

        return measurand

    def loadTaxonomy(self):
        for taxon in self._mii_taxons_dict:
            self.getMeasurandObject(self._mii_taxons_dict[taxon])

    def extractTaxonomy(self):
        with self._path.open() as f:
            mii_dict = xmltodict.parse(
                f.read(), process_namespaces=True, namespaces=self._namespaces
            )

        mii_taxons_dict = {}
        mii_taxons_flat = []
        # Populate QuantityKind Table
        for taxon in mii_dict[self._namespaces["mtc"]][
            self._namespaces["taxon"]
        ]:
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
                },
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
                            ]
                        },
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
                        else:
                            _dict = {
                                "@name": parm["@name"],
                                "@optional": parm["@optional"],
                                "mtc:Definition": parm[
                                    self._namespaces["definition"]
                                ],
                            }
                        mii_taxons_dict[taxon["@name"]][
                            "mtc:Parameter"
                        ].append(_dict)
            mii_taxons_flat.append(mii_taxons_dict[taxon["@name"]])

        self._mii_taxons_dict = mii_taxons_dict
        self._mii_taxons_list = mii_taxons_flat

    def flattenTaxonomy(self):
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
