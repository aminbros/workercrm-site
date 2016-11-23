from ..models import Worker, Config, ConfigData
from django.contrib.auth.models import User
from ..apimod import ApiError, mk_readsingle_call, mk_readmulti_call
from .configdata import configdataColumns, configdataRelatedKeys, \
  gcCheckAConfigData
from .config import configColumns
import json

configdataRelatedKeys.append("worker_set")

workerColumns = ("id", "name","key","baseconfig_id","configdata_id")
_wbcColumn = ({
  'name': "baseconfig",
  'type': "onerel",
  'columns': configColumns
},)
_wcdColumn = ({
  'name': "configdata",
  'type': "onerel",
  'columns': configdataColumns
},)

def _getWorkersFunc(user, offset, limit, query):
  records = Worker.objects.filter(owner=user) \
      if query == "" or query == None \
      else Worker.objects.filter(owner=user, name__icontains=query)
  return (workerColumns, records[offset:offset+limit], records.count())
getWorkers = mk_readmulti_call(_getWorkersFunc)
getWorker = mk_readsingle_call( \
  lambda user, id, with_baseconfig, with_configdata: \
    (workerColumns + (_wcdColumn if with_configdata else ()) + \
     (_wbcColumn if with_baseconfig else ()),
     Worker.objects.get(id=id, owner=user)))

def createWorker(user, name, key, **kwargs):
  baseconfig = None \
               if kwargs['baseconfig_id'] == None \
               else Config.objects.get(owner=user, id=kwargs['baseconfig_id'])
  if 'configdata' in kwargs:
    confdict = json.loads(kwargs['configdata'])
    if type(confdict) != dict:
      raise ValueError("configdata value(dict expected): %s" % confdict)
    confdata = ConfigData(owner=user, data=confdict)
    confdata.inherits = baseconfig.configdata if baseconfig != None else None
    confdata.save()
  else:
    confdata = ConfigData.objects.get(owner=user, id=kwargs['configdata_id'])
    confdata.inherits = baseconfig.configdata if baseconfig != None else None
    confdata.save()
  worker = Worker(owner=user, name=name, key=key, configdata=confdata,
                  baseconfig=baseconfig)
  worker.save()
  return {
    "id": worker.id
  }

def updateWorker(user, id, **kwargs):
  worker = Worker.objects.get(id=id)
  baseconfig_changed = False
  if kwargs['baseconfig_id'] != None:
    if len(kwargs['baseconfig_id']) == 0:
      worker.baseconfig_id = None
      baseconfig_changed = True
    else:
      baseconfig = Config.objects.get(owner=user, id=kwargs['baseconfig_id'])
      worker.baseconfig = baseconfig
      baseconfig_changed = True
  if 'configdata' in kwargs:
    confdict = json.loads(kwargs['configdata'])
    if type(confdict) != dict:
      raise ValueError("configdata value(dict expected): %s" % confdict)
    worker.configdata.data = confdict
    confdata = worker.configdata
    if baseconfig_changed:
      confdata.inherits = worker.baseconfig.configdata \
                          if worker.baseconfig != None else None
    worker.configdata.save()
  else:
    confdata = ConfigData.objects.get(owner=user, id=kwargs['configdata_id'])
    if baseconfig_changed:
      confdata.inherits = worker.baseconfig.configdata \
                          if worker.baseconfig != None else None
    worker.configdata = confdata
  for strvalkey in ('name','key'):
    if kwargs[strvalkey] != None:
      setattr(worker, strvalkey, kwargs[strvalkey])
  worker.save()
  return {
    "id": str(worker.id)
  }

def deleteWorker(user, id):
  worker = Worker.objects.get(owner=user, id=id)
  configdata = worker.configdata
  worker.delete()
  gcCheckAConfigData(configdata)
  return {}

