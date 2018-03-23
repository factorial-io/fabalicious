from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red, yellow
from lib.utils import validate_dict
from lib.configuration import data_merge
from lib import configuration
import os

class RsyncMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'rsync'

  @staticmethod
  def validateConfig(config):
    if 'git' not in config['needs']:
      return { 'needs': 'please add git to your list of needs!' }

    if config['needs'].index('rsync') < config['needs'].index('git'):
      return { 'needs': 'rsync needs to be after git, check your needs!' }

    if config['gitRootFolder'] == config['rootFolder']:
      return { 'rootFolder': 'rootFolder needs to be different as your gitRootFolder' }

    return validate_dict(['gitRootFolder', 'rootFolder'], config)

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    defaults['rsyncOptions'] = {}

  @staticmethod
  def applyConfig(config, settings):
    config['rsyncOptions'] = data_merge(settings['rsyncOptions'], config['rsyncOptions'])
    BaseMethod.addExecutables(config, ['mkdir', 'rsync'])


  def deploy(self, config, **kwargs):
    exclude = config['rsyncOptions']['exclude'] if 'exclude' in config['rsyncOptions'] else []

    exclude = exclude + [
      os.path.relpath(config['siteFolder'], config['rootFolder']),
      os.path.relpath(config['filesFolder'], config['rootFolder'])
    ]

    options = {
      'source': config['gitRootFolder'] + '/',
      'target': config['rootFolder']
    }

    if 'include' in config['rsyncOptions']:
      options['include'] = '--include ' + ' --include '.join(config['rsyncOptions']['include'])

    if len(exclude):
      options['exclude'] = '--exclude ' + ' --exclude '.join(exclude)

    cmd = '#!rsync -avCh --delete {include} {exclude} {source} {target}'.format(**options)

    with self.runLocally(config), self.cd(config['gitRootFolder']):
      self.run_quietly('#!mkdir -p %s' % config['rootFolder']);
      self.run(cmd)


  def createApp(self, config, stage, dockerConfig, **kwargs):
    targetPath = dockerConfig['rootFolder'] + '/' + config['docker']['projectFolder']
    self.setExecutables(config)




