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
        self._updateResources = parms['update_resources']
        self._use_cmc_api = parms['use_cmc_api']
        self._kcdb_path = parms['kcdb']
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

    def _getRefDataQuantities(self):
        print("Get Reference data quantities from KCDB API")
        output = requests.get(f'{self.api_ref}/quantity', headers=self.headers)
        result = json.loads(output.content)
        for q in result["referenceData"]:
            self._transformKcdbObject(q,
                                      model.KcdbQuantity,
                                      self._schemas['quantity'])

    def _getKcdbRefData(self):

        self._getRefDataQuantities()

        print("Get REference data from KCDB API") 
        output = requests.get(f'{self.api_ref}/metrologyArea',
                              headers=self.headers,
                              params={'domainCode': 'PHYSICS'})
        
        result = json.loads(output.content)
        reference_data = {}
        
        self._service_classifications.append(['Id',
                                              'Area Id',
                                              'Area',
                                              'Branch Id',
                                              'Branch',
                                              'Service',
                                              'Subservice',
                                              'IndividualService']
                                             )
        reference_data['physics_areas'] = {}
        reference_data['service_classification'] = {}
        for area in result["referenceData"]:
            id_ = area['id']
            reference_data['physics_areas'][area["label"]] = area['value']
            output_branch = requests.get(f'{self.api_ref}/branch?areaId={id_}',
                                         headers=self.headers
                                         )
            result_branch = json.loads(output_branch.content)
            print(area)
            self._transformKcdbObject(area,
                                      model.KcdbArea,
                                      self._schemas['area'])
            for branch in result_branch['referenceData']:
                id_b = branch['id']
                output_service = requests.get(f'{self.api_ref}/service?branchId={id_b}',
                                              headers=self.headers
                                              )
                result_service = json.loads(output_service.content)
                self._transformKcdbObject(branch,
                                          model.KcdbBranch,
                                          self._schemas['branch'])
                for service in result_service['referenceData']:
                    id_s = service['id']
                    output_subservice = requests.get(f'{self.api_ref}/subService?serviceId={id_s}', headers=self.headers)
                    result_subservice = json.loads(output_subservice.content)
                    self._transformKcdbObject(service,
                                              model.KcdbService,
                                              self._schemas['service']
                                              )
                    for subservice in result_subservice['referenceData']:
                        id_c = subservice['id']
                        output_idvservice = requests.get(f'{self.api_ref}/individualService?subServiceId={id_c}', headers=self.headers)
                        self._transformKcdbObject(subservice,
                                                  model.KcdbSubservice,
                                                  self._schemas['subservice']
                                                  )
                        try:
                            result_idvservice = json.loads(output_idvservice.content)
                        except Exception:
                            print("Invalid Subservice id")
                            print(area['value'],
                                  branch['label'],
                                  branch['value'],
                                  service['label'],
                                  service['value'],
                                  subservice['label'],
                                  subservice['value']
                                  )
                            continue
                        
                        for idvservice in result_idvservice['referenceData']:
                            id_v = ".".join([area['label'],
                                             branch['label'],
                                             service['label'],
                                             subservice['label'],
                                             idvservice['label']])
                            reference_data['service_classification'][id_v] = [
                                           area['value'],
                                           branch['label'],
                                           branch['value'],
                                           service['value'],
                                           subservice['value'],
                                           idvservice['value']]
                                                                            
                            serviceClass = [id_v,
                                            area['label'],
                                            area['value'],
                                            branch['label'],
                                            branch['value'],
                                            service['value'],
                                            subservice['value'],
                                            idvservice['value']
                                            ]
                            self._transformKcdbObject(idvservice,
                                                      model.KcdbIndividualService,
                                                      self._schemas['individualservice']
                                                      )
                            self._transformKcdbServiceClass(serviceClass)
    
    def _getCmcMetadataLocal(self, cmc, obj):
        area = (self.Session.query(model.KcdbArea)
                .filter(model.KcdbArea.id == obj['area']['id'])
                .first()
                )
        branch = (self.Session.query(model.KcdbBranch)
                  .filter(model.KcdbBranch.id == obj['branch']['id'])
                  .first()
                  )
        service = (self.Session.query(model.KcdbService)
                   .filter(model.KcdbService.id == obj['service']['id'])
                   .first()
                   )
        subservice = (self.Session.query(model.KcdbSubservice)
                      .filter(model.KcdbSubservice.id == obj['subservice']['id'])
                      .first()
                      )
        individualservice = (self.Session.query(model.KcdbIndividualService)
                             .filter(model.KcdbIndividualService.id == obj['individualservice']['id'])
                             .first()
                             )
        quantity = (self.Session.query(model.KcdbQuantity)
                    .filter(model.KcdbQuantity.id == obj['quantity']['id'])
                    .first()
                    )
        instrument = (self.Session.query(model.KcdbInstrument)
                      .filter(model.KcdbInstrument.id == obj['instrument']['id'])
                      .first()
                      )
        if obj['instrumentmethod']:
            instrumentMethod = (self.Session.query(model.KcdbInstrumentMethod)
                                .filter(model.KcdbInstrumentMethod.id == obj['instrumentmethod']['id'])
                                .first()
                                )
        else:
            instrumentMethod = None

        if area:
            cmc.area = area
        if branch:
            cmc.branch = branch
        if service:
            cmc.service = service
        if subservice:
            cmc.subservice = subservice
        if individualservice:
            cmc.individualservice = individualservice
        if quantity:
            cmc.quantity = quantity
        if instrument:
            cmc.instrument = instrument
        else:
            instrument = model.KcdbInstrument()
            instrument.value = obj['instrument']
            self.Session.add(instrument)
            cmc.instrument = instrument
        if instrumentMethod:
            cmc.instrumentmethod = instrumentMethod
        else:
            instrumentMethod = model.KcdbInstrumentMethod()
            instrumentMethod.value = obj['instrumentmethod']
            self.Session.add(instrumentMethod)
            cmc.instrumentmethod = instrumentMethod
        for parm in obj['parameters']:
            parameter = model.KcdbParameter()
            parameter.name = parm['name']
            parameter.value = parm['value']
            self.Session.add(parameter)
            cmc.parameters.append(parameter)
    
    def _getCmcMetadata(self, cmc, obj):
        print(f'Linking CMC {cmc.id}, {cmc.kcdbCode} with metadata')
        print(f'Kcdb cmc object {obj["id"]}, {obj["kcdbCode"]}')
        print(obj)
        area = (self.Session.query(model.KcdbArea)
                .filter(model.KcdbArea.label == obj['metrologyAreaLabel'])
                .first()
                )
        branch = (self.Session.query(model.KcdbBranch)
                  .filter(model.KcdbBranch.value == obj['branchValue'])
                  .first()
                  )
        service = (self.Session.query(model.KcdbService)
                   .filter(model.KcdbService.value == obj['serviceValue'])
                   .first()
                   )
        subservice = (self.Session.query(model.KcdbSubservice)
                      .filter(model.KcdbSubservice.value == obj['subServiceValue'])
                      .first()
                      )
        individualservice = (self.Session.query(model.KcdbIndividualService)
                             .filter(model.KcdbIndividualService.value == obj['individualServiceValue'])
                             .first()
                             )
        quantity = (self.Session.query(model.KcdbQuantity)
                    .filter(model.KcdbQuantity.value == obj['quantityValue'])
                    .first()
                    )
        
        instrument = (self.Session.query(model.KcdbInstrument)
                    .filter(model.KcdbInstrument.value == obj['instrument'])
                    .first()
                    )
         
        instrumentMethod = (self.Session.query(model.KcdbInstrumentMethod)
                    .filter(model.KcdbInstrumentMethod.value == obj['instrumentMethod'])
                    .first()
                    )
        print(obj['instrumentMethod'], instrumentMethod)
        if area:
            cmc.area = area
        if branch:
            cmc.branch = branch
        if service:
            cmc.service = service
        if subservice:
            cmc.subservice = subservice
        if individualservice:
            cmc.individualservice = individualservice
        if quantity:
            cmc.quantity = quantity
        if instrument:
            cmc.instrument = instrument
        else:
            instrument = model.KcdbInstrument()
            instrument.value = obj['instrument']
            self.Session.add(instrument)
            cmc.instrument = instrument
        if instrumentMethod:
            cmc.instrumentmethod = instrumentMethod
        else:
            instrumentMethod = model.KcdbInstrumentMethod()
            instrumentMethod.value = obj['instrumentMethod']
            self.Session.add(instrumentMethod)
            cmc.instrumentmethod = instrumentMethod
        for parm in obj['parameters']:
            parameter = model.KcdbParameter()
            parameter.name = parm['parameterName']
            parameter.value = parm['parameterValue']
            self.Session.add(parameter)
            cmc.parameters.append(parameter)

        print(cmc.instrumentmethod) 
    
    def _getPhysicsCmcDataLocal(self):
        with open(f'{self._kcdb_path}/kcdb_cmc.json') as f:
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
                        'baseUnit': obj['baseUnit'],
                        'uncertaintyBaseUnit': obj['uncertaintyBaseUnit'],
                        'comments': obj['comments']
                    }
                    cmc = model.KcdbCmcSchema().load(
                        payload, session=self.Session
                    )
                    self.Session.add(cmc)
                    self._getCmcMetadataLocal(cmc, obj)

    def _getPhysicsCmcData(self):
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
        
        for area in self.Session.query(model.KcdbArea).all():
            data['metrologyAreaLabel'] = area.label
            print(f"Request CMC for {area}")
            data['page'] = 0
            while True:
                output = requests.post(f'{api_ref}',
                                       headers=headers,
                                       data=json.dumps(data)
                                       )
                result = json.loads(output.content)
                if data['page'] == 0:
                    print(result['data'][0].keys())
                if len(result['data']) == 0:
                    break
                data['page'] = data['page']+1
                for obj in result['data']:
                    cmc = (
                            self.Session.query(model.KcdbCmc)
                            .filter(model.KcdbCmc.id == int(obj['id']))
                            .first()
                            )
                    
                    if not cmc:
                        try:
                            payload = {
                                'id': obj['id'],
                                'kcdbCode': obj['kcdbCode'],
                                'baseUnit': obj['cmcBaseUnit']['unit'],
                                'uncertaintyBaseUnit': obj['cmcUncertaintyBaseUnit']['unit'],
                                'comments': obj['comments']
                            }
                            cmc = self._schemas['cmc'].load(
                                payload, session=self.Session
                            )
                            self.Session.add(cmc)
                            self._getCmcMetadata(cmc, obj)
                        except Exception as e:
                            print(obj)
                            raise e

    def updateLocalResources(self):
        with open('resources/kcdb/kcdb_service_classifications.csv','w', newline='') as fs:
            writer = csv.writer(fs)
            writer.writerows(self._service_classifications)
   
    def _dumpKcdbRefData(self, out_, type_, schema_):
        with open(f'{self._kcdb_path}/kcdb_{out_}.json', 'w') as fs:
            objs = self.Session.query(type_).all()
            result = schema_.dump(objs, many=True)
            # print(result)
            json.dump(result, fs, ensure_ascii=False, indent=4)

    def _dumpKcdbCmcData(self, out_, type_, schema_):
        with open(f'{self._kcdb_path}/kcdb_{out_}.json', 'w') as fs:
            objs = self.Session.query(type_).all()
            result = schema_.dump(objs, many=True)
            # print(result)
            json.dump(result, fs, ensure_ascii=False, indent=4)
    
    def dumpKcdbRefData(self):
        self._dumpKcdbRefData('area',
                              model.KcdbArea,
                              model.KcdbAreaSchema()
                              )
        self._dumpKcdbRefData('branch',
                              model.KcdbBranch,
                              model.KcdbBranchSchema()
                              )
        self._dumpKcdbRefData('service',
                              model.KcdbService,
                              model.KcdbServiceSchema()
                              )
        self._dumpKcdbRefData('subservice',
                              model.KcdbSubservice,
                              model.KcdbSubserviceSchema()
                              )
        self._dumpKcdbRefData('individualservice',
                              model.KcdbIndividualService,
                              model.KcdbIndividualServiceSchema()
                              )
        self._dumpKcdbRefData('quantity',
                              model.KcdbQuantity,
                              model.KcdbQuantitySchema()
                              )
        self._dumpKcdbCmcData('cmc',
                              model.KcdbCmc,
                              model.KcdbCmcSchema()
                              )
        self._dumpKcdbRefData('serviceclass',
                              model.KcdbServiceClass,
                              model.KcdbServiceClassSchema())
        self._dumpKcdbRefData('instrument',
                              model.KcdbInstrument,
                              model.KcdbInstrumentSchema())
        self._dumpKcdbRefData('instrumentmethod',
                              model.KcdbInstrumentMethod,
                              model.KcdbInstrumentMethodSchema())

    def _getKcdbRefDataLocal(self):
        self._transformKcdbRefDataLocal('quantity',
                                        model.KcdbQuantity,
                                        model.KcdbQuantitySchema()
                                        )
        self._transformKcdbRefDataLocal('area',
                                        model.KcdbArea,
                                        model.KcdbAreaSchema()
                                        )
        self._transformKcdbRefDataLocal('branch',
                                        model.KcdbBranch,
                                        model.KcdbBranchSchema()
                                        )
        self._transformKcdbRefDataLocal('service',
                                        model.KcdbService,
                                        model.KcdbServiceSchema()
                                        )
        self._transformKcdbRefDataLocal('subservice',
                                        model.KcdbSubservice,
                                        model.KcdbSubserviceSchema()
                                        )
        self._transformKcdbRefDataLocal('individualservice',
                                        model.KcdbIndividualService,
                                        model.KcdbIndividualServiceSchema()
                                        )
        self._transformKcdbRefDataLocal('instrument',
                                        model.KcdbInstrument,
                                        model.KcdbInstrumentSchema()
                                        )
        self._transformKcdbRefDataLocal('instrumentmethod',
                                        model.KcdbInstrumentMethod,
                                        model.KcdbInstrumentMethodSchema()
                                        )
        self._transformKcdbServiceClassLocal()
    
    def _transformKcdbRefDataLocal(self, out_, type_, schema_):
        with open(f'{self._kcdb_path}/kcdb_{out_}.json') as f:
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

    def _transformKcdbServiceClassLocal(self):
        with open(f'{self._kcdb_path}/kcdb_serviceclass.json') as f:
            objs = json.load(f)
            for obj in objs:
                service = (
                           self.Session.query(model.KcdbServiceClass)
                           .filter(model.KcdbServiceClass.id == obj['id'])
                           .first()
                           )
                if not service:
                    payload = {
                        "id": obj['id'],
                        "area_id": obj['area_id'],
                        "area": obj['area'],
                        "branch_id": obj['branch_id'],
                        "branch": obj['branch'],
                        "service": obj['service'],
                        "subservice": obj['subservice'],
                        "individualservice": obj['individualservice']
                    }
                    service = self._schemas["serviceclass"].load(
                        payload, session=self.Session
                    )
                    self.Session.add(service)
    
    def _transformKcdbServiceClass(self, _data):
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
            self._getKcdbRefDataLocal('quantity', 
                                      model.KcdbQuantity, 
                                      model.KcdbQuantitySchema())
        else:
            self.getRefDataQuantities()
    
    def loadServices(self):
        if self._use_api is False:
            self._getKcdbRefDataLocal()
            if self._use_cmc_api is True:
                self._getPhysicsCmcData()
                if self._updateResources is True:
                    self.dumpKcdbRefData()
            else:
                self._getPhysicsCmcDataLocal()
            
            #with open(self._services_path) as f:
            #    reader = csv.reader(f)
            #    next(reader)
            #    for row in reader:
            #        self._load_service(row)
        elif self._use_api is True:
            self._getKcdbRefData()
            self._getPhysicsCmcData()
            if self._updateResources is True:
                self.dumpKcdbRefData()

            #for s in self._service_classifications[1:]:
            #    self._load_service(s)



