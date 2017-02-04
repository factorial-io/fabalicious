from base import BaseMethod
from fabric.api import *

class ComposerMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'composer'

  def getArgs(self,config):
    args = '-n'
    if config['type'] != 'dev' and config['type'] != 'test':
      args += ' --no-dev --optimize-autoloader'

    return args


  def resetPrepare(self, config, **kwargs):
    self.setRunLocally(config)

    with self.cd(config['gitRootFolder']):
      self.run_quietly('composer install %s' % self.getArgs(config))

  def updateApp(self, config,**kwargs):
    self.setRunLocally(config)
    with self.cd(config['gitRootFolder']):
      self.run_quietly('composer update %s' % self.getArgs(config))

  def composer(self, config, command, **kwargs):
    self.setRunLocally(config)
    with self.cd(config['gitRootFolder']):
      self.run_quietly('composer %s' % command)



