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
        self._units_path = Path(parms["units"]).resolve()
        self._conversions_path = Path(parms["conversions"]).resolve()
        self._casts_path = Path(parms["casts"]).resolve()
        self._functions_path = Path(parms["functions"]).resolve()
        # self._dbpath = (self._path_root / 'data/nrc_mis.db')
        self._aspects = {}
        self._scales = {}
        self._units = {}
        self._schemas = {
            "aspect": model.AspectSchema(),
            "scale": model.ScaleSchema(),
            "unit": model.UnitSchema(),
            "transform": model.TransformFunctionSchema(),
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

   
    def etlFunctions(self):

        if self._doapi is True:
            response = requests.get(self._api + "/functions")
            print(response.status_code)
            if response.status_code  == 200: 
                for item in response.json():
                    fcn = (
                        self.Session.query(model.Aspect)
                        .filter(model.TransformFunction.id == item['id'])
                        .first()
                    )
                    if not fcn:
                        data_ = {
                            "id": item['id'], 
                            "ml_name": item["ml_name"],

                        }
                        fcn = self._schemas["transform"].load(
                            data_, session=self.Session
                        )
                        self.Session.add(fcn)

                    
        else:
            with self._functions_path.open() as f:
                data = json.load(f)
                for item in data:
                    fcn = (
                        self.Session.query(model.TransformFunction)
                        .filter(model.TransformFunction.id == item['id'])
                        .first()
                    )
                    if not fcn:
                        data_ = {
                            "id": item['id'], 
                            "ml_name": item["ml_name"],

                        }
                        fcn = self._schemas["transform"].load(
                            data_, session=self.Session
                        )
                        self.Session.add(fcn)

    def getScaleAspectAssociations(self):
        # Obtaining ScaleAspect associations more complicated
        # M-layer (concept package) conversions only associate scales
        # use the conversion file name to look up the aspect?
        # Casting associates scale-aspect pairs
        # Scales_for associate many scales to the same aspect
        if self._doapi is True:
            response = requests.get(self._api + "/conversions")
            print(response.status_code)
            if response.status_code  == 200: 
                for conversion in response.json():
                    aspect = (
                        self.Session.query(model.Aspect)
                        .filter(model.Aspect.id == key)
                        .first()
                    )
                    
        else:
            with self._conversions_path.open() as f:
                data = json.load(f)
                for conversion in data:
                    aspect = (
                        self.Session.query(model.Aspect)
                        .filter(model.Aspect.id == conversion['aspect_id'])
                        .first()
                    )
                    src_scale = (
                        self.Session.query(model.Scale)
                        .filter(model.Scale.id == conversion['src_scale_id'])
                        .first()
                    )
                    dst_scale = (
                        self.Session.query(model.Scale)
                        .filter(model.Scale.id == conversion['dst_scale_id'])
                        .first()
                    )
                    aspect.scales.append(src_scale)
                    aspect.scales.append(dst_scale)
                    
                    data_ = {
                            "src_scale_id": conversion['src_scale_id'],
                            "dst_scale_id": conversion['dst_scale_id'],
                            "aspect_id": conversion['aspect_id'],
                    }
                    
                    #obj_ = self._schemas["conversion"].load(
                    #        data_, session=self.Session
                    #    )
                    cnv = model.Conversion(src_scale_id=conversion['src_scale_id'],
                                           dst_scale_id=conversion['dst_scale_id'],
                                           aspect_id=conversion['aspect_id'],
                                           function_id=conversion['function_id'])
                    self.Session.add(cnv)
                    #except:
                    #    print("Could not create conversion")
                    #    print("src: {}, dst: {}, aspect: {}".format(conversion['src_scale_id'],
                     #                                               conversion['dst_scale_id'],
                      #                                              conversion['aspect_id']))
                        
            
            with self._casts_path.open() as f:
                data = json.load(f)
                for conversion in data:
                    src_aspect = (
                        self.Session.query(model.Aspect)
                        .filter(model.Aspect.id == conversion['src_aspect_id'])
                        .first()
                    )
                    src_scale = (
                        self.Session.query(model.Scale)
                        .filter(model.Scale.id == conversion['src_scale_id'])
                        .first()
                    )
                    dst_aspect = (
                        self.Session.query(model.Aspect)
                        .filter(model.Aspect.id == conversion['dst_aspect_id'])
                        .first()
                    )
                    dst_scale = (
                        self.Session.query(model.Scale)
                        .filter(model.Scale.id == conversion['dst_scale_id'])
                        .first()
                    )
                    src_aspect.scales.append(src_scale)
                    dst_aspect.scales.append(dst_scale)
                    cst = model.Cast(src_scale_id=conversion['src_scale_id'],
                                     dst_scale_id=conversion['dst_scale_id'],
                                     src_aspect_id=conversion['src_aspect_id'],
                                     dst_aspect_id=conversion['dst_aspect_id'],
                                     function_id=conversion['function_id'])
                    self.Session.add(cst)
                    
        
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
                    "ml_name": self._units[key]["ml_name"],
                    "symbol": self._units[key]["symbol"],
                    "reference": self._units[key]["reference"],
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
