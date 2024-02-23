#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2024 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
import csv
from pathlib import Path
from miiflask.flask import model


class KcdbMapper:
    def __init__(self, session, parms):
        # self._path_root = get_project_root()

        self._services_path = Path(parms["services"]).resolve()
        self._quantities_path = Path(parms["quantities"]).resolve()
        self._services = {}
        self._quantities = {}
        self._schemas = {
            "service": model.KcdbServiceSchema(),
            "quantity": model.KcdbQuantitySchema(),
        }
        self.Session = session

    def loadQuantities(self):
        with open(self._quantities_path) as f:
            reader = csv.reader(f)
            for row in reader:
                quantity = (
                self.Session.query(model.KcdbQuantity)
                .filter(model.KcdbQuantity.name == row[0])
                .first()
                )
                if not quantity:
                    data_ = {
                        "name": row[0],
                    }
                    quantity = self._schemas["quantity"].load(
                        data_, session=self.Session
                    )
                    self.Session.add(quantity)
    
    def loadServices(self):
        with open(self._services_path) as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                service = (
                self.Session.query(model.KcdbService)
                .filter(model.KcdbService.id == row[0])
                .first()
                )
                if not service:
                    data_ = {
                        "id": row[0],
                        "area_id": row[1],
                        "area": row[2],
                        "branch_id": row[3],
                        "branch": row[4],
                        "service": row[5],
                        "subservice": row[6],
                        "individualservice": row[7]
                    }
                    service = self._schemas["service"].load(
                        data_, session=self.Session
                    )
                    self.Session.add(service)



