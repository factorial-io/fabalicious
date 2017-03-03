from base import BaseMethod
from fabric.api import *

class DrushMakeMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'drushmake'

  def getArgs(self,config):
    self.setRunLocally(config)
    if 'makefile' not in config:
      config.update({'makefile':'drush.make'})

    return config['gitRootFolder'] + '/' + config['makefile'] + ' ' + config['rootFolder'] + ' --concurrency=8 --force-complete -vvv ' 

  def updateApp(self, config,**kwargs):
    # this needs work.
    self.setRunLocally(config)
    with self.cd(config['rootFolder']):
      self.run_quietly('drush make %s updatedCore' % self.getArgs(config))

  def resetPrepare(self, config, **kwargs):
    self.setRunLocally(config)
    with self.cd(config['rootFolder']):
      self.run_quietly('drush make %s --no-core ' % self.getArgs(config))
