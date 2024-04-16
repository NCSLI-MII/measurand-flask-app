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
            "serviceclass": model.KcdbServiceClassSchema(),
            "quantity": model.KcdbQuantitySchema(),
            "area": model.KcdbAreaSchema(),
            "branch": model.KcdbBranchSchema(),
            "service": model.KcdbServiceSchema(),
            "subservice": model.KcdbSubserviceSchema(),
            "individualservice": model.KcdbIndividualServiceSchema(),
            'cmc': model.KcdbCmcSchema()
        }
        self.Session = session

    def getRefDataQuantities(self):
        print("Get Reference data quantities from KCDB API")
        output = requests.get(f'{self.api_ref}/quantity', headers=self.headers)
        result = json.loads(output.content)
                
        for q in result["referenceData"]:
            self._transformKcdbObject(q, model.KcdbQuantity, self._schemas['quantity'])
            #self._quantities.append(q['value'])
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
            self._transformKcdbObject(area, model.KcdbArea, self._schemas['area'])
            for branch in result_branch['referenceData']:
                id_b = branch['id']
                output_service = requests.get(f'{self.api_ref}/service?branchId={id_b}', headers=self.headers)
                result_service = json.loads(output_service.content)
                self._transformKcdbObject(branch, model.KcdbBranch, self._schemas['branch'])
                for service in result_service['referenceData']:
                    id_s = service['id']
                    output_subservice = requests.get(f'{self.api_ref}/subService?serviceId={id_s}', headers=self.headers)
                    result_subservice = json.loads(output_subservice.content)
                    self._transformKcdbObject(service, model.KcdbService, self._schemas['service'])
                    for subservice in result_subservice['referenceData']:
                        id_c = subservice['id']
                        output_idvservice = requests.get(f'{self.api_ref}/individualService?subServiceId={id_c}', headers=self.headers)
                        self._transformKcdbObject(subservice, model.KcdbSubservice, self._schemas['subservice'])
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
                            self._transformKcdbObject(idvservice, model.KcdbIndividualService, self._schemas['individualservice'])

    def getPhysicsCMCData(self):
        if self._use_api is False:
            with open('../../resources/kcdb/kcdb_cmc.json') as f:
                objs = json.load(f)
                for obj in objs:
                    cmc = (
                            self.Session.query(model.KcdbCmc)
                            .filter(model.KcdbCmc.id == obj['id'])
                            .first()
                            )
                    if not cmc:
                        payload = {
                            'id': obj['id'],
                            'kcdbCode': obj['kcdbCode'],
                        }
                        cmc = model.KcdbCmcSchema().load(
                            payload, session=self.Session
                        )
                        self.Session.add(cmc)
            return

        api_ref = 'https://www.bipm.org/api/kcdb/cmc/searchData/physics'
        headers = {'accept': 'application/json',
                   'Content-Type': 'application/json'
                   }
        data = {
          "page": 0,
          "pageSize": 20,
          "metrologyAreaLabel": None,
          "showTable": False,
          "countries": [
            "CA",
          ],
        }
        fields = None
        ntotal=0
        #print(f"Query CMCs for {disciplines}")
        
        for area in self.Session.query(model.KcdbArea).all():
            data['metrologyAreaLabel'] = area.label
            print(f"Request CMC for {area}")
            results=[]
            data['page'] = 0
            while True: 
                print("Page", data['page'])
                output = requests.post(f'{api_ref}',headers=headers,data=json.dumps(data))
                #print(output.headers)
                result = json.loads(output.content)
                if data['page'] == 0:
                    print(result['data'][0].keys())
                if len(result['data']) == 0:
                    break
                data['page'] = data['page']+1
                for cmc in result['data']:
                    print(cmc)
                    obj = (
                            self.Session.query(model.KcdbCmc)
                            .filter(model.KcdbCmc.id == int(cmc['id']))
                            .first()
                            )
                    if not obj:
                        payload = {
                            'id': cmc['id'],
                            'kcdbCode': cmc['kcdbCode']
                        }
                        obj = self._schemas['cmc'].load(
                            payload, session=self.Session
                        )
                        self.Session.add(obj)
                        area = (self.Session.query(model.KcdbArea)
                                .filter(model.KcdbArea.label == cmc['metrologyAreaLabel'])
                                .first()
                                )
                        branch = (self.Session.query(model.KcdbBranch)
                                  .filter(model.KcdbBranch.value == cmc['branchValue'])
                                  .first()
                                  )
                        service = (self.Session.query(model.KcdbService)
                                   .filter(model.KcdbService.value == cmc['serviceValue'])
                                   .first()
                                   )
                        subservice = (self.Session.query(model.KcdbSubservice)
                                      .filter(model.KcdbSubservice.value == cmc['subServiceValue'])
                                      .first()
                                      )
                        individualservice = (self.Session.query(model.KcdbIndividualService)
                                             .filter(model.KcdbIndividualService.value == cmc['individualServiceValue'])
                                             .first()
                                             )
                        quantity = (self.Session.query(model.KcdbQuantity)
                                    .filter(model.KcdbQuantity.value == cmc['quantityValue'])
                                    .first()
                                    )

                        if area:
                            obj.area = area
                        if branch:
                            obj.branch = branch
                        if service:
                            obj.service = service
                        if subservice:
                            obj.subservice = subservice
                        if individualservice:
                            obj.individualservice = individualservice
                        if quantity:
                            obj.quantity = quantity

    def updateLocalResources(self):
        with open('resources/kcdb/kcdb_service_classifications.csv','w', newline='') as fs:
            writer = csv.writer(fs)
            writer.writerows(self._service_classifications)
   
    def _dumpKcdbRefData(self, out_, type_, schema_):
        with open(f'../../resources/kcdb/kcdb_{out_}.json', 'w') as fs:
            objs = self.Session.query(type_).all()
            result = schema_.dump(objs, many=True)
            # print(result)
            json.dump(result, fs, ensure_ascii=False, indent=4)

    def dumpKcdbCmcData(self):
        self._dumpKcdbRefData('cmc', model.KcdbCmc, model.KcdbCmcSchema())

    def dumpKcdbRefData(self):
        self._dumpKcdbRefData('area', model.KcdbArea, model.KcdbAreaSchema())
        self._dumpKcdbRefData('branch', model.KcdbBranch, model.KcdbBranchSchema())
        self._dumpKcdbRefData('service', model.KcdbService, model.KcdbServiceSchema())
        self._dumpKcdbRefData('subservice', model.KcdbSubservice, model.KcdbSubserviceSchema())
        self._dumpKcdbRefData('individualservice', model.KcdbIndividualService, model.KcdbIndividualServiceSchema())
        self._dumpKcdbRefData('quantity', model.KcdbQuantity, model.KcdbQuantitySchema())
        

    def getKcdbRefDataLocal(self):
        self._getKcdbRefDataLocal('area', model.KcdbArea, model.KcdbAreaSchema())
        self._getKcdbRefDataLocal('branch', model.KcdbBranch, model.KcdbBranchSchema())
        self._getKcdbRefDataLocal('service', model.KcdbService, model.KcdbServiceSchema())
        self._getKcdbRefDataLocal('subservice', model.KcdbSubservice, model.KcdbSubserviceSchema())
        self._getKcdbRefDataLocal('individualservice', model.KcdbIndividualService, model.KcdbIndividualServiceSchema())
        
    
    def _getKcdbRefDataLocal(self, out_, type_, schema_):
        with open(f'../../resources/kcdb/kcdb_{out_}.json') as f:
            objs = json.load(f)
            for obj in objs:
                self._transformKcdbObject(obj, type_, schema_)
    
    def _transformKcdbObject(self, data_, type_, schema_):
        obj = (
                self.Session.query(type_)
                .filter(type_.id == data_['id'])
                .first()
                )
        if not obj:
            payload = {
                'id': data_['id'],
                'value': data_['value'],
                'label': data_['label']
            }
            obj = schema_.load(
                payload, session=self.Session
            )
            self.Session.add(obj)

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
            self.Session.query(model.KcdbServiceClass)
            .filter(model.KcdbServiceClass.id == _data[0])
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
                service = self._schemas["serviceclass"].load(
                    payload, session=self.Session
                )
                self.Session.add(service)


    def loadQuantities(self):
        if self._use_api is False:
            self._getKcdbRefDataLocal('quantity', model.KcdbQuantity, model.KcdbQuantitySchema())
        else:
            self.getRefDataQuantities()

    
    def loadServices(self):
        if self._use_api is False:
            self.getKcdbRefDataLocal()
            with open(self._services_path) as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    self._load_service(row)
        else:
            self.getReferenceData()
            for s in self._service_classifications[1:]:
                self._load_service(s)



