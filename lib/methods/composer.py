from base import BaseMethod
from fabric.api import *

class ComposerMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'composer'

  def getArgs(self,config):
    args = ''
    if config['type'] != 'dev':
      args += ' --no-dev --optimize-autoloader'

    return args


  def resetPrepare(self, config, **kwargs):
    with cd(config['gitRootFolder']):
      self.run_quietly('composer install %s' % self.getArgs(config))

  def updateApp(self, config,**kwargs):
    with cd(config['gitRootFolder']):
      self.run_quietly('composer update %s' % self.getArgs(config))

  def composer(self, config, command, **kwargs):
    with cd(config['gitRootFolder']):
      self.run_quietly('composer %s' % command)



