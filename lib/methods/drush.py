from base import BaseMethod
from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red
from fabric.network import *
from fabric.context_managers import settings as _settings
from lib import configuration
from lib import utils
import re
from lib.utils import validate_dict

class DrushMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'drush7' or methodName == 'drush8' or methodName == 'drush'

  @staticmethod
  def validateConfig(config):
    result = validate_dict(['siteFolder', 'filesFolder'], config)
    if not result:
      return result

    if 'database' in config:
      return validate_dict(['user', 'pass', 'name'], config['database'], 'database')

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    defaults['configurationManagement'] = settings['configurationManagement']
    defaults['database'] = {}

  @staticmethod
  def applyConfig(config, settings):
    if 'host' not in config['database']:
      config['database']['host'] = 'localhost'
    BaseMethod.addExecutables(config, ['drush', 'mysql', 'mysqladmin', 'gunzip', 'rsync', 'scp', 'grep'])

  def reset(self, config, **kwargs):
    self.setRunLocally(config)

    if 'withPasswordReset' not in kwargs:
      kwargs['withPasswordReset'] = True

    if self.methodName == 'drush8':
      uuid = config['uuid'] if 'uuid' in config else False
      if not uuid:
        uuid = configuration.getSettings('uuid')

      if not uuid:
        print red('No uuid found in fabfile.yaml. config-import may fail!')

    with self.cd(config['siteFolder']):
      if config['type'] == 'dev':
        admin_user = configuration.getSettings('adminUser', 'admin')

        if 'withPasswordReset' in kwargs and kwargs['withPasswordReset'] in [True, 'True', '1']:
          self.run_drush('user-password %s --password="admin"' % admin_user)
        with warn_only():
          self.run_quietly('chmod -R 777 ' + config['filesFolder'])
      with warn_only():
        if configuration.getSettings('deploymentModule'):
          self.run_drush('en -y ' + configuration.getSettings('deploymentModule'))

      if self.methodName == 'drush8':
        self.run_drush('updb --entity-updates -y')
      else:
        self.run_drush('updb -y')

      script_fn = self.factory.get('script', 'runScript')

      with warn_only():
        if self.methodName == 'drush8':
          if uuid:
            self.run_drush('cset system.site uuid %s -y' % uuid)
          if 'configurationManagement' in config:
            for key, cmds in config['configurationManagement'].iteritems():
              script_fn(config, script=cmds, rootFolder=config['siteFolder'])
        else:
          self.run_drush('fra -y')

        fn = self.factory.get('script', 'runTaskSpecificScript')
        fn('reset', config, **kwargs)

        if self.methodName == 'drush8':
          self.run_drush('cr')
        else:
          self.run_drush(' cc all')


  def run_drush(self, cmd, expand_command = True):
    env.output_prefix = False
    if expand_command:
      cmd = '#!drush ' + cmd
    args = ['running']
    if self.verbose_output:
      args = []

    with hide(*args):
      self.run(cmd)
    env.output_prefix = True


  def backupSql(self, config, backup_file_name):
    self.setRunLocally(config)

    with self.cd(config['siteFolder']):
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
    self.setRunLocally(config)
    with self.cd(config['siteFolder']):
      self.run_drush(kwargs['command'])


  def backup(self, config, **kwargs):
    self.setRunLocally(config)

    baseName = kwargs['baseName']
    filename = config['backupFolder'] + "/" + '--'.join(baseName) + ".sql"
    self.backupSql(config, filename)
    if config['supportsZippedBackups']:
      filename += '.gz'
    print green('Database dump at "%s"' % filename)

  def listBackups(self, config, results, **kwargs):
    files = self.list_remote_files(config['backupFolder'], ['*.sql', '*.sql.gz'])
    for file in files:
      hash = re.sub('\.(sql\.gz|sql)$', '', file)
      backup_result = self.get_backup_result(config, file, hash, 'drush')
      if backup_result:
        results.append(backup_result)

  def restore(self, config, files=False, cleanupBeforeRestore=False, **kwargs):

    file = self.get_backup_result_for_method(files, 'drush')
    if not file:
      return

    sql_name_target = config['backupFolder'] + '/' + file['file']
    self.importSQLFromFile(config, sql_name_target, cleanupBeforeRestore)


  def importSQLFromFile(self, config, sql_name_target, cleanupBeforeRestore=False):

    with self.runLocally(config), self.cd(config['siteFolder']):
      if cleanupBeforeRestore:
        self.run_drush('sql-drop -y')

      if config['supportsZippedBackups']:
        self.run_drush('#!gunzip -c '+ sql_name_target + ' | $(#!drush sql-connect)', False)
      else:
        self.run_drush('sql-cli < ' + sql_name_target)

      print(green('SQL restored from "%s"' % sql_name_target))


  def copyDBFrom(self, config, source_config=False, **kwargs):
    self.setRunLocally(config)

    target_config = config
    sql_name_source = source_config['tmpFolder'] + '/' + config['config_name'] + '.sql'
    sql_name_target = target_config['tmpFolder'] + '/' + config['config_name'] + '_target.sql'

    if source_config['supportsZippedBackups']:
      sql_name_target += '.gz'

    source_host_string = join_host_strings(source_config['user'], source_config['host'], source_config['port'])

    # create dump on source.
    with _settings( host_string=source_host_string ), self.runLocally(source_config):
      self.backupSql(source_config, sql_name_source)

    # copy dump to target:
    if source_config['supportsZippedBackups']:
      sql_name_source += '.gz'

    args = utils.ssh_no_strict_key_host_checking_params

    cmd = '#!scp -P {port} {args} {user}@{host}:{sql_name_source} {sql_name_target} '.format(  args=args,
      sql_name_source=sql_name_source,
      sql_name_target=sql_name_target,
      **source_config
      )
    self.run(cmd)

    with _settings(host_string=source_host_string), self.runLocally(source_config):
      self.run_quietly('rm -f %s' % sql_name_source)

    self.importSQLFromFile(target_config, sql_name_target, True)
    # self.run_quietly('rm -f %s' % sql_name_target)


  def restoreSQLFromFile(self, config, sourceFile, **kwargs):

    targetSQLFileName = config['tmpFolder'] + '/manual_upload.sql'

    fileName, fileExtension = os.path.splitext(sourceFile)
    zipped = fileExtension == '.gz'
    if zipped:
      targetSQLFileName += '.gz'

    if config['runLocally']:
      local('cp %s %s' % (sourceFile, targetSQLFileName))
    else:
      put(sourceFile, targetSQLFileName)

    self.importSQLFromFile(config, targetSQLFileName)

    with self.runLocally(config):
      self.run_quietly('rm -f %s' % targetSQLFileName)

  def install(self, config, ask='True', distribution='minimal', **kwargs):
    self.setRunLocally(config)

    if 'database' not in config:
      print red('Missing database configuration!')
      exit(1)

    configuration.validate_dict(['user', 'pass', 'name', 'host'], config['database'], 'Missing database configuration: ')

    print green('Installing fresh database for "%s"' % config['config_name'])

    o = config['database']

    with self.cd(config['siteFolder']):
      self.run_quietly('mkdir -p %s' % config['siteFolder'])
      mysql_cmd  = 'CREATE DATABASE IF NOT EXISTS {name}; GRANT ALL PRIVILEGES ON {name}.* TO \'{user}\'@\'%\' IDENTIFIED BY \'{pass}\'; FLUSH PRIVILEGES;'.format(**o)

      self.run_quietly('#!mysql -h {host} -u {user} --password={pass} -e "{mysql_command}"'.format(mysql_command=mysql_cmd, **o), 'Creating database')

      with warn_only():
        self.run_quietly('chmod u+w {siteFolder}'.format(**config))
        self.run_quietly('chmod u+w {siteFolder}/settings.php'.format(**config))
        self.run_quietly('rm -f {siteFolder}/settings.php.old'.format(**config))
        self.run_quietly('mv {siteFolder}/settings.php {siteFolder}/settings.php.old 2>/dev/null'.format(**config))

        sites_folder = os.path.basename(config['siteFolder'])
        options = ''
        if ask.lower() == 'false' or ask.lower() == '0':
          options = ' -y'
        options += ' --sites-subdir='+sites_folder
        options += ' --account-name=%s' % configuration.getSettings('adminUser', 'admin')
        options += ' --account-pass=admin'
        if 'prefix' in o:
          options += " --db-prefix='%s'" % o['prefix']

        options += '  --db-url=mysql://' + o['user'] + ':' + o['pass'] + '@' + o['host'] + '/' +o ['name']
        self.run_drush('site-install ' + distribution + ' ' + options)

        if self.methodName == 'drush7':
          self.run_drush('en features -y')

        deploymentModule = configuration.getSettings('deploymentModule')
        if deploymentModule:
          self.run_drush('en -y %s' % deploymentModule)

    if self.methodName == 'drush8':
      self.setupConfigurationManagement(config)

  def setupConfigurationManagement(self, config):
    with self.runLocally(config), self.cd(config['siteFolder']):
      self.run_quietly('chmod u+w .');
      self.run_quietly('chmod u+w settings.php');
      for configName in config['configurationManagement']:
        cmd = '#!grep -q -F \'$config_directories["{0}"] = "../config/{0}";\' settings.php || echo \'$config_directories["{0}"] = "../config/{0}";\' >> settings.php'.format(configName)
        self.run_quietly(cmd)



  def updateApp(self, config, version=7, **kwargs):
    self.setRunLocally(config)

    if 'composer' in config['needs']:
      # ignore update, as composer will handle this.
      return;

    # download drupal
    with cd(config['rootFolder']):
      self.run_quietly('rm -rf /tmp/drupal-update')
      self.run_quietly('mkdir -p /tmp/drupal-update')
      self.run_drush('dl --destination="/tmp/drupal-update" --default-major="%d" drupal ' % version)

    # copy files to root-folder
    with(cd('/tmp/drupal-update')), hide('running'):
      drupal_folder = run('ls').stdout.strip()
      # print drupal_folder

      self.run('#!rsync -rav --no-o --no-g %s/* %s' % (drupal_folder, config['rootFolder']) )


    # remove temporary files
    with self.cd(config['rootFolder']):
      self.run_quietly('rm -rf /tmp/drupal-update')

    print green("Updated drupal successfully to '%s'." % (drupal_folder))

  def waitForDatabase(self, config):
    self.setRunLocally(config)
    available = False
    tries = 0
    while not available and tries < 10:
      try:
        with settings(hide('warnings', 'running', 'output'), warn_only=True):
          output = self.run_quietly("#!mysqladmin -u{user} --password={pass} -h {host} ping".format(**config['database']))
          if output.return_code == 0:
            return True
      except:
        print "exception"
        pass

      time.sleep(5)
      print "Wait another 5 secs for the database ..."

    print red('Database not available!')
    return False


  def createApp(self, config, stage, dockerConfig, **kwargs):
    if stage=='install':
      self.waitForDatabase(config)
      self.install(config, ask='0')
      self.reset(config, withPasswordReset=True)

  def preflight(self, task, config, **kwargs):
    if task == 'install':
      self.waitForDatabase(config)

