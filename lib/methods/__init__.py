import inspect
from types import TypeType
from base import BaseMethod;
from git import GitMethod;


from types import TypeType
class Factory(object):
  @staticmethod
  def get(name):
    methodClasses = [j for (i,j) in globals().iteritems() if isinstance(j, TypeType) and issubclass(j, BaseMethod)]
    for methodClass in methodClasses:
      if methodClass.supports(name):
        return methodClass()
    #if research was unsuccessful, raise an error
    raise ValueError('No method supporting "%s" found.' % name)

def callImpl(methodName, taskName, optional, *args):
  m = Factory().get(methodName)
  print m
  if hasattr(m, taskName) and inspect.ismethod(getattr(m, taskName)):
    m[taskName](args)
  elif not optional:
    raise ValueError('Task "%s" in method "%s" not found!' % (taskName, methodName))

def call(methodName, taskName, *args):
  callImpl(methodName, taskName, False, args),

