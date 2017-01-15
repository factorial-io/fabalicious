from base import BaseMethod
from fabric.api import *
from lib.utils import SSHTunnel, RemoteSSHTunnel
from fabric.colors import green, red
from lib import configuration
from fabric.contrib.files import exists

import copy

class DrupalConsoleMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'drupalconsole'

  def run_install(self, config, **kwargs):
    with cd(config['tmpFolder']):
      run('curl https://drupalconsole.com/installer -L -o drupal.phar')
      run('mv drupal.phar /usr/local/bin/drupal')
      run('chmod +x /usr/local/bin/drupal')
      run('drupal init')

      print green('Drupal Console installed successfully.')

  def run_drupalconsole(self, config, command):
    with cd(config['rootFolder']):
      bin_path = '%s/vendor/bin/drupal' % config['gitRootFolder']
      if exists(bin_path):
        run('%s %s' % (bin_path, command))
      elif exists('/usr/local/bin/drupal'):
        run('drupal %s' % command)
      else:
        print red('Could not find drupal executable. You can install a global one with drupal:install')


  def drupalconsole(self, config, **kwargs):
    if kwargs['command'] == 'install':
        self.run_install(config)
        return
    self.run_drupalconsole(config, kwargs['command'])

