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
import requests
import json
from miiflask.flask import model


class KcdbMapper:
    def __init__(self, session, parms):
        # self._path_root = get_project_root()
        self._use_api = parms["use_api"]
        self.api_ref = 'https://www.bipm.org/api/kcdb/referenceData' 
        self.headers = {'accept': 'application/json',
                'Content-Type': 'application/json'
                }
        self._services_path = Path(parms["services"]).resolve()
        self._quantities_path = Path(parms["quantities"]).resolve()
        self._service_classifications = []
        self._quantities = []
        self._schemas = {
            "service": model.KcdbServiceSchema(),
            "quantity": model.KcdbQuantitySchema(),
        }
        self.Session = session

    def getRefDataQuantities(self):
        print("Get Reference data quantities from KCDB API")
        output = requests.get(f'{self.api_ref}/quantity', headers=self.headers)
        result = json.loads(output.content)
        
        for q in result["referenceData"]:
            self._quantities.append(q['value'])
        #print(self._quantities)
    
    def getReferenceData(self):
        print("Get REference data from KCDB API")
        output = requests.get(f'{self.api_ref}/metrologyArea', headers=self.headers, params={"domainCode":"PHYSICS"})
        
        result = json.loads(output.content)
        reference_data = {}
        
        self._service_classifications.append(['Id', 'Area Id', 'Area', 'Branch Id', 'Branch', 'Service', 'Subservice', 'IndividualService'])
        reference_data['physics_areas'] = {}
        reference_data['service_classification'] = {}
        
        for area in result["referenceData"]:
            id_ = area['id']
            reference_data['physics_areas'][area["label"]] = area['value']
            output_branch = requests.get(f'{self.api_ref}/branch?areaId={id_}', headers=self.headers)
            result_branch = json.loads(output_branch.content)
            print(area)
            for branch in result_branch['referenceData']:
                id_b = branch['id']
                output_service = requests.get(f'{self.api_ref}/service?branchId={id_b}', headers=self.headers)
                result_service = json.loads(output_service.content)
                
                for service in result_service['referenceData']:
                    id_s = service['id']
                    output_subservice = requests.get(f'{self.api_ref}/subService?serviceId={id_s}', headers=self.headers)
                    result_subservice = json.loads(output_subservice.content)
                    
                    for subservice in result_subservice['referenceData']:
                        id_c = subservice['id']
                        output_idvservice = requests.get(f'{self.api_ref}/individualService?subServiceId={id_c}', headers=self.headers)
                        try:
                            result_idvservice = json.loads(output_idvservice.content)
                        except:
                            print("Invalid Subservice id")
                            print(area['value'], branch['label'], branch['value'], service['label'], service['value'], subservice['label'],subservice['value'])
                            continue
                        
                        for idvservice in result_idvservice['referenceData']:
                            id_v = ".".join([area['label'],branch['label'],service['label'],subservice['label'], idvservice['label']])
                            reference_data['service_classification'][id_v] = [area['value'], 
                                    branch['label'], 
                                    branch['value'], 
                                    service['value'], 
                                    subservice['value'], 
                                    idvservice['value']]
                            self._service_classifications.append(
                                    [id_v,area['label'], 
                                    area['value'], 
                                    branch['label'], 
                                    branch['value'], 
                                    service['value'], 
                                    subservice['value'],
                                    idvservice['value']])
            

    
    def updateLocalResources(self):
        with open('resources/kcdb/kcdb_service_classifications.csv','w', newline='') as fs:
            writer = csv.writer(fs)
            writer.writerows(self._service_classifications)

    def _load_quantity(self, _data):
            quantity = (
            self.Session.query(model.KcdbQuantity)
            .filter(model.KcdbQuantity.name == _data)
            .first()
            )
            if not quantity:
                payload = {
                    "name": _data,
                }
                quantity = self._schemas["quantity"].load(
                    payload, session=self.Session
                )
                self.Session.add(quantity)

    def _load_service(self, _data):
            service = (
            self.Session.query(model.KcdbService)
            .filter(model.KcdbService.id == _data[0])
            .first()
            )
            if not service:
                payload = {
                    "id": _data[0],
                    "area_id": _data[1],
                    "area": _data[2],
                    "branch_id": _data[3],
                    "branch": _data[4],
                    "service": _data[5],
                    "subservice": _data[6],
                    "individualservice": _data[7]
                }
                service = self._schemas["service"].load(
                    payload, session=self.Session
                )
                self.Session.add(service)


    def loadQuantities(self):
        if self._use_api is False:
            with open(self._quantities_path) as f:
                reader = csv.reader(f)
                for row in reader:
                    self._load_quantity(row[0])
        else:
            self.getRefDataQuantities()
            for q in self._quantities:
                self._load_quantity(q)

    
    def loadServices(self):
        if self._use_api is False:
            with open(self._services_path) as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    self._load_service(row)
        else:
            self.getReferenceData()
            for s in self._service_classifications[1:]:
                self._load_service(s)



