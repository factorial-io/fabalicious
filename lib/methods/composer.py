from base import BaseMethod
from fabric.api import *

class ComposerMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'composer'


  def resetPrepare(self, config):
    self.run_quietly('composer install')


