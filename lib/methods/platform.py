from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
from lib import configuration
import copy

class PlatformMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'platform'

  @staticmethod
  def getOverrides():
    return 'drush'

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


