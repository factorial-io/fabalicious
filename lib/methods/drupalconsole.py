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
    self.setRunLocally(config)
    with self.cd(config['tmpFolder']):
      self.run('curl https://drupalconsole.com/installer -L -o drupal.phar')
      self.run('mv drupal.phar /usr/local/bin/drupal')
      self.run('chmod +x /usr/local/bin/drupal')
      self.run('drupal init')

      print green('Drupal Console installed successfully.')

  def run_drupalconsole(self, config, command):
    self.setRunLocally(config)
    with self.cd(config['rootFolder']):
      bin_path = '%s/vendor/bin/drupal' % config['gitRootFolder']
      if self.exists(bin_path):
        self.run('%s %s' % (bin_path, command))
      elif self.exists('/usr/local/bin/drupal'):
        self.run('drupal %s' % command)
      else:
        print red('Could not find drupal executable. You can install a global one with drupal:install')


  def drupalconsole(self, config, **kwargs):
    self.setRunLocally(config)
    if kwargs['command'] == 'install':
        self.run_install(config)
        return
    self.run_drupalconsole(config, kwargs['command'])

