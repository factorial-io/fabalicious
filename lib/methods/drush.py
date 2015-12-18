from base import BaseMethod
from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red
from lib import configuration

class DrushMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'drush7' or methodName == 'drush8' or methodName == 'drush'

  def runCommonScripts(self, config):
   common_scripts = configuration.getSettings('common')
   if common_scripts and config['type'] in common_scripts:
     script = common_scripts[config['type']]
     self.factory.call('script', 'runScript', config, script = script)


  def reset(self, config, **kwargs):
    if self.methodName == 'drush8':
      uuid = config['uuid'] if 'uuid' in config else False
      if not uuid:
        uuid = configuration.getSettings('uuid')

      if not uuid:
        print red('No uuid found in fabfile.yaml. config-import may fail!')

    with cd(config['siteFolder']):
      if config['type'] == 'dev':
        if 'withPasswordReset' in kwargs and kwargs['withPasswordReset'] in [True, 'True', '1']:
          self.run_drush('user-password admin --password="admin"')
        with warn_only():
          self.run_quietly('chmod -R 777 ' + config['filesFolder'])
      with warn_only():
        if configuration.getSettings('deploymentModule'):
          self.run_drush('en -y ' + configuration.getSettings('deploymentModule'))
      # self.run_drush('updb -y')
      with warn_only():
        if self.methodName == 'drush8':
          if uuid:
            self.run_drush('cset system.site uuid %s -y', uuid)
          self.run_drush('config-import staging -y')
        else:
          self.run_drush('fra -y')

        self.runCommonScripts(config)

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


  def backupSql(self, config, backup_file_name):
    with cd(config['siteFolder']):
      with warn_only():
        dump_options = ''
        if configuration.getSettings('sqlSkipTables'):
          dump_options = '--structure-tables-list=' + ','.join(configuration.getSettings('sqlSkipTables'))

        self.run_quietly('mkdir -p ' + config['backupFolder'])
        self.run_quietly('rm -f '+backup_file_name)
        if config['supportsZippedBackups']:
          self.run_quietly('rm -f '+backup_file_name+'.gz')
          dump_options += ' --gzip'

      self.run_drush('sql-dump ' + dump_options + ' --result-file=' + backup_file_name)


  def drush(self, config, **kwargs):
    with cd(config['siteFolder']):
      self.run_drush(kwargs['command'])


  def backup(self, config, **kwargs):
    baseName = kwargs['baseName']
    filename = config['backupFolder'] + "/" + '--'.join(baseName) + ".sql"
    self.backupSql(config, filename)
    if config['supportsZippedBackups']:
      filename += '.gz'
    print green('Database dump at "%s"' % filename)



