from yapsy.IPlugin import IPlugin
from lib.methods import BaseMethod

class IMethodPlugin(BaseMethod, IPlugin):

  def __init__(self):
    pass

  def setNameAndFactory(self, name, factory):
    self.methodName = name
    self.factory = factory
