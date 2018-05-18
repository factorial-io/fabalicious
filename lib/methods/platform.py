import logging
log = logging.getLogger('fabric.fabalicious.platform')

from base import BaseMethod
from fabric.api import *
from lib import configuration
from drush import DrushMethod


import copy
import time


class PlatformMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'platform'

  @staticmethod
  def getOverrides():
    return 'drush'

  def __init__(self, name, factory):
    self.shadowed_drush = DrushMethod('drush8', factory)
    BaseMethod.__init__(self, name, factory)

  def run_install(self, config, **kwargs):
    local('curl -sS https://platform.sh/cli/installer | php');
    log.info('platform.sh client installed successfully.')

  def run_platform(self, config, command):
      local('platform %s' % command)

  def platform(self, config, **kwargs):
    if kwargs['command'] == 'install':
        self.run_install(config)
        return
    self.run_platform(config, kwargs['command'])

  def deploy(self, config, **kwargs):
    local('git push platform %s' % config['branch'])
    print 'Wait 10 secs for the installation to settle ...'
    time.sleep(10)


  def drush(self, config, **kwargs):
    self.shadowed_drush.drush(config, **kwargs)
