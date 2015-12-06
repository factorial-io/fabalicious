import inspect
from types import TypeType
from base import BaseMethod;
from git import GitMethod;

cache = {}

class Factory(object):


  @staticmethod
  def get(name):
    methodClasses = [j for (i,j) in globals().iteritems() if isinstance(j, TypeType) and issubclass(j, BaseMethod)]
    for methodClass in methodClasses:
      if methodClass.supports(name):
        return methodClass()
    #if research was unsuccessful, raise an error
    raise ValueError('No method supporting "%s" found.' % name)

def callImpl(methodName, taskName, optional, arguments):
  if methodName in cache:
    m = cache[methodName]
  else:
    m = Factory().get(methodName)
    cache[methodName] = m

  if hasattr(m, taskName) and inspect.ismethod(getattr(m, taskName)):
    fn = getattr(m, taskName)
    result = fn(*arguments)
    return result
  elif not optional:
    raise ValueError('Task "%s" in method "%s" not found!' % (taskName, methodName))

def call(methodName, taskName, *arguments):
  return callImpl(methodName, taskName, False, arguments)

