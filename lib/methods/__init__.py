import inspect
from types import TypeType
from base import BaseMethod
from git import GitMethod
from drush import DrushMethod

cache = {}

class Factory(object):


  @staticmethod
  def get(name):
    methodClasses = [j for (i,j) in globals().iteritems() if isinstance(j, TypeType) and issubclass(j, BaseMethod)]
    for methodClass in methodClasses:
      if methodClass.supports(name):
        return methodClass(name)
    #if research was unsuccessful, raise an error
    raise ValueError('No method supporting "%s" found.' % name)

def callImpl(methodName, taskName, configuration, optional, **kvargs):
  if methodName in cache:
    m = cache[methodName]
  else:
    m = Factory().get(methodName)
    cache[methodName] = m

  print 'Running task "%s" on method "%s"' % (taskName, methodName)
  if hasattr(m, taskName) and inspect.ismethod(getattr(m, taskName)):
    fn = getattr(m, taskName)
    result = fn(configuration, **kvargs)
    return result
  elif not optional:
    raise ValueError('Task "%s" in method "%s" not found!' % (taskName, methodName))

def call(methodName, taskName, configuration, **kvargs):
  return callImpl(methodName, taskName, configuration, False, **kvargs)

def runTask(configuration, taskName, **kvargs):
  runTaskImpl(configuration['needs'], taskName + "Prepare", configuration, **kvargs);
  runTaskImpl(configuration['needs'], taskName, configuration, **kvargs);
  runTaskImpl(configuration['needs'], taskName + "Finished", configuration, **kvargs);

def runTaskImpl(methodNames, taskName, configuration, **kvargs):
  for methodName in methodNames:
    callImpl(methodName, taskName, configuration, True, **kvargs)
