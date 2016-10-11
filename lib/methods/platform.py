from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
from lib import configuration
import copy

class PlatformMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'platform'

  def run_install(self, config, **kwargs):
    local('curl -sS https://platform.sh/cli/installer | php');
    print green('platform.sh client installed successfully.')

  def run_platform(self, config, command):
      local('platform %s' % command)

  def platform(self, config, **kwargs):
    if kwargs['command'] == 'install':
        self.run_install(config)
        return
    self.run_platform(config, kwargs['command'])

  def deploy(self, config, **kwargs):
    local('git push platform %s' % config['branch'])

  def backup(self, config, **kwargs):
    self.run_platform(config, 'snapshot:create -e %s' % config["branch"])

  def listBackups(self, config, results, **kwargs):
    self.run_platform(config, 'snapshot:list -e %s' % config["branch"])


