#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2023 Ryan Mackenzie White <ryan.white@nrc-cnrc.gc.ca>
#
# Distributed under terms of the Copyright © 2022 National Research Council Canada. license.

"""
Mappers for m-layer-concept data
Json data files added to nrc_mis
m-layer-concept develop commit 359c467
"""
import json
import uuid
import requests
from pathlib import Path
from miiflask.flask import model


class MlayerMapper:
    def __init__(self, session, parms):
        # self._path_root = get_project_root()
        self._api = parms["api_mlayer"]
        self._doapi = parms['use_api']
        self._scales_path = Path(parms["scales"]).resolve()
        self._aspects_path = Path(parms["aspects"]).resolve()
        # self._dbpath = (self._path_root / 'data/nrc_mis.db')
        self._aspects = {}
        self._scales = {}
        self._units = {}
        self._schemas = {
            "aspect": model.AspectSchema(),
            "scale": model.ScaleSchema(),
            "unit": model.UnitSchema()
        }
        self.Session = session

    def getTableIdentifier(self, uid):
        uuid_ = uuid.UUID(int=uid)
        return str(uuid_)

    def extractMlayerAspects(self):
        if self._doapi is True:
            response = requests.get(self._api + "/aspects")
            print(response.status_code)
           
            if response.status_code  == 200: 
                for aspect in response.json():
                    self._aspects[aspect["id"]] = aspect
        else:
            with self._aspects_path.open() as f:
                data = json.load(f)
                for aspect in data:
                    self._aspects[aspect["id"]] = aspect

    def extractMlayerUnits(self):
        if self._doapi is True:        
            response = requests.get(self._api + "/units")
            print(response.status_code)
            if response.status_code  == 200: 
                for unit in response.json():
                    self._units[unit["id"]] = unit
        else:
            try:
                with self._units_path.open() as f:
                    data = json.load(f)
                    for unit in data:
                        self._units[unit["id"]] = unit
            except:
                print("Units file not found")
    
    def extractMlayerScales(self):
        if self._doapi is True:
            response = requests.get(self._api + "/scales")
            print(response.status_code)
            if response.status_code  == 200: 
                for scale in response.json():
                    self._scales[scale["id"]] = scale
        else:
            with self._scales_path.open() as f:
                data = json.load(f)
                for scale in data:
                    self._scales[scale["id"]] = scale

    def getScaleAspectAssociations(self):
        # Obtaining ScaleAspect associations more complicated
        # M-layer (concept package) conversions only associate scales
        # use the conversion file name to look up the aspect?
        # Casting associates scale-aspect pairs
        # Scales_for associate many scales to the same aspect
        mltypes = ["conversion", "scales_for"]
        associations = {}
        for _type in mltypes:
            for path in Path(self._path / _type).rglob("*json"):
                print(path)
                tag = path.name.split("/")[-1].split(".")[0]

                if tag in self._aspects.keys():
                    print(tag)
                    associations[tag] = []
                    try:
                        with path.open() as f:
                            data = json.load(f)
                            if _type == "conversion":
                                for cnv in data:
                                    associations[tag].append(cnv["src"])
                                    associations[tag].append(cnv["dst"])
                            if _type == "scales_for":
                                for cnv in data:
                                    associations[tag].append(cnv["src"])
                                    associations[tag].append(cnv["dst"])
                            if _type == "casting":
                                pass
                                # for cnv in data:
                                # associations[cnv['src'][1]]
                    except Exception as e:
                        print("Cannot open ", path.name)
                        print(e)
                    associations[tag] = set(
                        tuple(i) for i in associations[tag]
                    )

        return associations

    def loadAspectCollection(self):
        for key in self._aspects:
            aspect = (
                self.Session.query(model.Aspect)
                .filter(model.Aspect.id == key)
                .first()
            )
            if not aspect:
                data_ = {
                    "id": key, 
                    "name":  self._aspects[key]["name"],
                    "ml_name":  self._aspects[key]["ml_name"],
                    "symbol":  self._aspects[key]["symbol"],
                    "reference":  self._aspects[key]["reference"]
                }
                aspect = self._schemas["aspect"].load(
                    data_, session=self.Session
                )
                self.Session.add(aspect)
                print(aspect.name)

    
    def loadUnitCollection(self):
        for key in self._units:
            unit = (
                self.Session.query(model.Unit)
                .filter(model.Unit.id == key)
                .first()
            )
            if not unit:
                data_ = {
                    "id": key,
                    "name": self._units[key]["name"],
                    #"scale_type": self._scales[key]["type"],
                }
                unit = self._schemas["unit"].load(
                    data_, session=self.Session
                )
                self.Session.add(unit)
    
    def loadScaleCollection(self):
        for key in self._scales:
            # uid = self.getTableIdentifier(self._scales[key][1])
            scale = (
                self.Session.query(model.Scale)
                .filter(model.Scale.id == key)
                .first()
            )
            if not scale:
                #print(self._scales[key])
                data_ = {
                    "id": key,
                    "ml_name": self._scales[key]["ml_name"],
                    #"unit_id": self._scales[key]["unit_id"],
                    #"scale_type": self._scales[key]["type"],
                }
                scale = self._schemas["scale"].load(
                    data_, session=self.Session
                )
                unit = (
                    self.Session.query(model.Unit)
                    .filter(model.Unit.id == self._scales[key]["unit_id"])
                    .first()
                )
                scale.unit = unit
                self.Session.add(scale)


if __name__ == "__main__":
    mapper = MlayerMapper()
    mapper.loadMlayerAspects()
    mapper.loadMlayerScales()
    mapper.getAspectCollection()
    mapper.getScaleCollection()
    # mapper.getScaleAspectAssociations()
    # pprint.pprint(mapper._aspects, indent=2)
    # pprint.pprint(mapper._scales, indent=2)
