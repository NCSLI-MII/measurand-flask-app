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
from sqlalchemy import and_


class MlayerMapper:
    def __init__(self, session, parms):
        # self._path_root = get_project_root()
        self._api = parms["api_mlayer"]
        self._doapi = parms['use_api']
        self._resourceml = Path(parms["mlayer"])
        self._scales_path = (self._resourceml / "scales.json").resolve()
        self._aspects_path = (self._resourceml / "aspects.json").resolve()
        self._units_path = (self._resourceml / "units.json").resolve()
        self._conversions_path = ((self._resourceml / "conversions.json")
                                  .resolve()
                                  )
        self._casts_path = (self._resourceml / "casts.json").resolve()
        self._functions_path = (self._resourceml / "functions.json").resolve()
        # self._dbpath = (self._path_root / 'data/nrc_mis.db')
        self._aspects = {}
        self._scales = {}
        self._units = {}
        self._schemas = {
            "aspect": model.AspectSchema(),
            "scale": model.ScaleSchema(),
            "unit": model.UnitSchema(),
            "transform": model.TransformSchema(),
            'system': model.SystemSchema(),
            'dimension': model.DimensionSchema(),
            'prefix': model.PrefixSchema()
        }

        # Ordered list of transform to run
        # Defines the loading order needed to establish object relations
        # See getCollections
        self._transform = {
                'prefixes': self._transformPrefix,
                'systems': self._transformSystem,
                'dimensions': self._transformDimension,
                'aspects': self._transformAspect,
                'units': self._transformUnit,
                'scales': self._transformScale,
                'functions': self._transformFunction,
                }
        self._cache_objs = []
        self.Session = session

    def getTableIdentifier(self, uid):
        uuid_ = uuid.UUID(int=uid)
        return str(uuid_)

    def _transformAspect(self, obj):
        aspect = (
            self.Session.query(model.Aspect)
            .filter(model.Aspect.id == obj['id'])
            .first()
        )
        if aspect:
            return None
        if obj["name"] == "electric potential difference":
            obj["name"] = "voltage"
        # Conform with XML Schema Name
        obj['name'] = obj['name'].replace(" ", "_")
        data_ = {
            "id": obj['id'],
            "name": obj["name"],
            "ml_name": obj["ml_name"],
            "symbol": obj["symbol"],
            "reference": obj["reference"]
        }
        aspect = self._schemas["aspect"].load(
            data_, session=self.Session
        )
        return aspect

    def _transformPrefix(self, obj):
        prefix = (
            self.Session.query(model.Prefix)
            .filter(model.Prefix.id == obj['id'])
            .first()
        )
        if prefix:
            return None
        data_ = {
            "id": obj['id'],
            "name": obj["name"],
            "ml_name": obj["ml_name"],
            "symbol": obj["symbol"],
            "reference": obj["reference"],
            'numerator': float(obj['numerator'].replace('"', '')),
            'denominator': float(obj['denominator'].replace('"', ''))
        }
        # print(data_)
        prefix = self._schemas["prefix"].load(
            data_, session=self.Session
        )
        return prefix

    def _transformUnit(self, obj):
        unit = (
            self.Session.query(model.Unit)
            .filter(model.Unit.id == obj['id'])
            .first()
        )
        if unit:
            return None
        data_ = {
            "id": obj['id'],
            "name": obj["name"],
            "ml_name": obj["ml_name"],
            "symbol": obj["symbol"],
            "reference": obj["reference"],
        }
        unit = self._schemas["unit"].load(
            data_, session=self.Session
        )
        return unit

    def _transformScale(self, obj):

        scale = (
            self.Session.query(model.Scale)
            .filter(model.Scale.id == obj["id"])
            .first()
        )
        if scale:
            return None
        data_ = {
            "id": obj['id'],
            "ml_name": obj["ml_name"],
            #"unit_id": self._scales[key]["unit_id"],
            "scale_type": obj["type"],
        }
        scale = self._schemas["scale"].load(
             data_, session=self.Session
        )
        #scale = model.Scale(id=obj['id'],
        #                    ml_name=obj['ml_name'],
        #                    scale_type=obj['type'],
        #                    is_systematic=obj['is_systematic'],
        #                    )

        unit = (
            self.Session.query(model.Unit)
            .filter(model.Unit.id == obj["unit_id"])
            .first()
        )
        scale.unit = unit

        prefix = (
            self.Session.query(model.Prefix)
            .filter(model.Prefix.id == obj["prefix_id"])
            .first()
        )
        scale.prefix = prefix

        system_dimensions = (
            self.Session.query(model.Dimension)
            .filter(model.Dimension.id == obj["system_dimensions_id"])
            .first()
        )
        if system_dimensions:
            scale.system_dimensions = system_dimensions

        # TBD
        # Parent scale may not be loaded before derived scale
        # If root scale not loaded
        # cache obj and reload
        if obj['root_scale_id']:
            root_scale = (
                self.Session.query(model.Scale)
                .filter(model.Scale.id == obj["root_scale_id"])
                .first()
            )
            if not root_scale:
                self._cache_objs.append(obj)
                return None
            scale.root_scale = root_scale
        
        # TBD
        # validate self-referential table
        # otherwise, use adjacency table for model
        #
        if (obj['id'] == 'SC101' or obj['id'] == 'SC2'):
            print(obj)
            if scale.prefix:
                print(scale.prefix.id)
                print(scale.system_dimensions.id)
            if scale.root_scale:
                print(scale.root_scale.id)
        #    if scale.derived_scales:
        #        for s in scale.derived_scales:
        #            print(s.id)

        # print(self._schemas["scale"].dumps(scale)) 
             
        return scale

    def _transformFunction(self, obj):

        fcn = (
            self.Session.query(model.Transform)
            .filter(model.Transform.id == obj['id'])
            .first()
        )
        if fcn:
            return None
        data_ = {
            "id": obj['id'],
            "ml_name": obj["ml_name"],
            "py_function": obj["py_function"],
            "py_names_in_scope": obj["py_names_in_scope"],
            "comments": obj["comments"]
        }
        fcn = self._schemas["transform"].load(
            data_, session=self.Session
        )
        return fcn

    def _transformDimension(self, obj):
        dimension = (
            self.Session.query(model.Dimension)
            .filter(model.Dimension.id == obj["id"])
            .first()
        )
        if dimension:
            return None
        data_ = {
            "id": obj['id'],
            "exponents": obj["exponents"],
        }
        dimension = self._schemas['dimension'].load(
            data_, session=self.Session
        )
        system = (
            self.Session.query(model.System)
            .filter(model.System.id == obj["formal_system_id"])
            .first()
        )
        dimension.formal_system = system
        return dimension

    def _transformSystem(self, obj):
        system = (
            self.Session.query(model.System)
            .filter(model.System.id == obj['id'])
            .first()
        )
        if system:
            return None
        data_ = {
            "id": obj['id'],
            "ml_name": obj["ml_name"],
            "symbol": obj["symbol"],
            "n": obj["n"],
            "basis": obj["basis"],
            "reference": obj['reference']
        }
        system = self._schemas['system'].load(data_, session=self.Session)
        return system

    def _loadCollection(self, type_, lst):
        while lst:
            obj = self._transform[type_](lst.pop())
            if not obj:
                continue
            self.Session.add(obj)

    def getCollections(self):
        for collection in self._transform.keys():
            print(collection)
            self._getCollection(collection)

    def _getCollection(self, type_):
        if self._doapi is True:
            response = requests.get(f'{self._api}/{type_}')
            print(response.status_code)
            if response.status_code == 200:
                self._loadCollection(type_, response.json())
        else:
            with (self._resourceml / f'{type_}.json').resolve().open() as f:
                self._loadCollection(type_, json.load(f))
        if len(self._cache_objs) > 0:
            self._loadCollection(type_, self._cache_objs)

    def _transformConversion(self, obj):
        aspect = (self.Session.query(model.Aspect)
                  .filter(model.Aspect.id == obj['aspect_id'])
                  .first()
                  )
        src_scale = (
            self.Session.query(model.Scale)
            .filter(model.Scale.id == obj['src_scale_id'])
            .first()
        )
        dst_scale = (
            self.Session.query(model.Scale)
            .filter(model.Scale.id == obj['dst_scale_id'])
            .first()
        )
        aspect.scales.append(src_scale)
        aspect.scales.append(dst_scale)

        # TBD
        # Marshmallow serilization
        cnv = model.Conversion(src_scale_id=obj['src_scale_id'],
                               dst_scale_id=obj['dst_scale_id'],
                               aspect_id=obj['aspect_id'],
                               transform_id=obj['function_id'],
                               parameters=obj['parameters'])
        return cnv

    def _transformCast(self, obj):
        src_aspect = (
            self.Session.query(model.Aspect)
            .filter(model.Aspect.id == obj['src_aspect_id'])
            .first()
        )
        src_scale = (
            self.Session.query(model.Scale)
            .filter(model.Scale.id == obj['src_scale_id'])
            .first()
        )
        dst_aspect = (
            self.Session.query(model.Aspect)
            .filter(model.Aspect.id == obj['dst_aspect_id'])
            .first()
        )
        dst_scale = (
            self.Session.query(model.Scale)
            .filter(model.Scale.id == obj['dst_scale_id'])
            .first()
        )
        src_aspect.scales.append(src_scale)
        dst_aspect.scales.append(dst_scale)
        cast = model.Cast(src_scale_id=obj['src_scale_id'],
                          dst_scale_id=obj['dst_scale_id'],
                          src_aspect_id=obj['src_aspect_id'],
                          dst_aspect_id=obj['dst_aspect_id'],
                          transform_id=obj['function_id'],
                          parameters=obj['parameters'])
        return cast

    def getScaleAspectAssociations(self):
        # Obtaining ScaleAspect associations more complicated
        # M-layer (concept package) conversions only associate scales
        # use the conversion file name to look up the aspect?
        # Casting associates scale-aspect pairs
        # Scales_for associate many scales to the same aspect
        if self._doapi is True:
            response = requests.get(self._api + "/conversions")
            print(response.status_code)
            if response.status_code == 200:
                for obj in response.json():
                    cnv = self._transformConversion(obj)
                    if (
                        self.Session.query(model.Conversion)
                        .filter(and_(model.Conversion.src_scale_id
                                     == cnv.src_scale_id,
                                     model.Conversion.dst_scale_id
                                     == cnv.dst_scale_id,
                                     model.Conversion.aspect_id
                                     == cnv.aspect_id))
                        .first()
                         ) is None:
                        self.Session.add(cnv)
                    # else:
                    #    print(f'Failed to add {cnv.src_scale_id},
                    # {cnv.dst_scale_id},
                    # {cnv.aspect_id} already exists')
            response = requests.get(self._api + "/casts")
            print(response.status_code)
            if response.status_code == 200:
                for obj in response.json():
                    cast = self._transformCast(obj)
                    if (
                        self.Session.query(model.Cast)
                        .filter(and_(model.Cast.src_scale_id
                                     == cast.src_scale_id,
                                     model.Cast.dst_scale_id
                                     == cast.dst_scale_id,
                                     model.Cast.src_aspect_id
                                     == cast.src_aspect_id,
                                     model.Cast.dst_aspect_id
                                     == cast.dst_aspect_id))
                        .first()
                         ) is None:
                        self.Session.add(cast)
                    # else:
                    #    print(f'Failed to add {cast.src_scale_id},
                    # {cast.dst_scale_id},
                    # {cast.src_aspect_id},
                    # {cast.dst_aspect_id} already exists')
        else:
            with self._conversions_path.open() as f:
                data = json.load(f)
                for obj in data:
                    conversion = self._transformConversion(obj)
                    if (
                        self.Session.query(model.Conversion)
                        .filter(and_(model.Conversion.src_scale_id
                                     == conversion.src_scale_id,
                                     model.Conversion.dst_scale_id
                                     == conversion.dst_scale_id,
                                     model.Conversion.aspect_id
                                     == conversion.aspect_id))
                        .first()
                         ) is None:
                        self.Session.add(conversion)
                    # else:
                    #    print(f'Failed to add {conversion.src_scale_id},
                    # {conversion.dst_scale_id},
                    # {conversion.aspect_id} already exists')
            with self._casts_path.open() as f:
                data = json.load(f)
                for obj in data:
                    cast = self._transformCast(obj)
                    if (
                        self.Session.query(model.Cast)
                        .filter(and_(model.Cast.src_scale_id
                                     == cast.src_scale_id,
                                     model.Cast.dst_scale_id
                                     == cast.dst_scale_id,
                                     model.Cast.src_aspect_id
                                     == cast.src_aspect_id,
                                     model.Cast.dst_aspect_id
                                     == cast.dst_aspect_id))
                        .first()
                         ) is None:
                        self.Session.add(cast)
                    # else:
                    #    print(f'Failed to add {cast.src_scale_id},
                    # {cast.dst_scale_id},
                    # {cast.src_aspect_id},
                    # {cast.dst_aspect_id} already exists')


if __name__ == "__main__":
    mapper = MlayerMapper()
    mapper.loadMlayerAspects()
    mapper.loadMlayerScales()
    mapper.getAspectCollection()
    mapper.getScaleCollection()
    # mapper.getScaleAspectAssociations()
    # pprint.pprint(mapper._aspects, indent=2)
    # pprint.pprint(mapper._scales, indent=2)
