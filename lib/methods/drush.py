from base import BaseMethod
from fabric.api import *
from fabric.state import output, env
from lib import configuration

class DrushMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'drush7' or methodName == 'drush8'

  def reset(self, config, **kwargs):
    with cd(env.config['siteFolder']):
      if config['useForDevelopment'] == True:
        if 'withPasswordReset' in kwargs and kwargs['withPasswordReset'] in [True, 'True', '1']:
          self.run_drush('user-password admin --password="admin"')
        with warn_only():
          self.run_quietly('chmod -R 777 ' + config['filesFolder'])
      with warn_only():
        if configuration.getSettings('deploymentModule'):
          self.run_drush('en -y ' + configuration.getSettings('deploymentModule'))
      self.run_drush('updb -y')
      with warn_only():
        if self.methodName == 'drush8':
          self.run_drush('config-import staging -y')
        else:
          self.run_drush('fra -y')

        self.run_common_commands()
        if self.methodName == 'drush8':
          self.run_drush('cr')
        else:
          self.run_drush(' cc all')

  def run_drush(self, cmd, expand_command = True):
    env.output_prefix = False
    if expand_command:
      cmd = 'drush ' + cmd
    args = ['running']
    if self.verbose_output:
      args = []

    with hide(*args):
      run(cmd)
    env.output_prefix = True







