from base import BaseMethod
from fabric.api import *

class ComposerMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'composer'

  @staticmethod
  def applyConfig(config, settings):
    BaseMethod.addExecutables(config, ['composer'])

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    if 'composerRootFolder' not in config:
      config['composerRootFolder'] = config['gitRootFolder']


  def getArgs(self,config):
    args = '-n'
    if config['type'] != 'dev' and config['type'] != 'test':
      args += ' --no-dev --optimize-autoloader'

    return args


  def resetPrepare(self, config, **kwargs):
    self.setRunLocally(config)

    with self.cd(config['composerRootFolder']):
      self.run_quietly('#!composer install %s' % self.getArgs(config))

  def updateApp(self, config,**kwargs):
    self.setRunLocally(config)
    with self.cd(config['composerRootFolder']):
      self.run_quietly('#!composer update %s' % self.getArgs(config))

  def composer(self, config, command, **kwargs):
    self.setRunLocally(config)
    with self.cd(config['composerRootFolder']):
      self.run_quietly('#!composer %s' % command)


  def createApp(self, config, stage, dockerConfig, **kwargs):
    if (stage == 'installDependencies'):
      self.setExecutables(config)

      targetPath = dockerConfig['rootFolder'] + '/' + config['docker']['projectFolder']
      with self.cd(targetPath):
        self.run('#!composer install %s' % self.getArgs(config))

