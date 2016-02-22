from base import BaseMethod
from fabric.api import *

class ComposerMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'composer'


  def resetPrepare(self, config, **kwargs):
    with cd(config['gitRootFolder']):
      self.run_quietly('composer install')


