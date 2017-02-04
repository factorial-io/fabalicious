from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
import datetime
import os.path
import re
from lib import utils
from lib import configuration
from lib.utils import validate_dict
from fabric.contrib.files import exists

class FilesMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'files'

  @staticmethod
  def validateConfig(config):
    return validate_dict(['rootFolder', 'siteFolder', 'filesFolder', 'backupFolder'], config)

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    pass

  @staticmethod
  def applyConfig(config, settings):
    config['filesFolder'] = config['rootFolder'] + config['filesFolder']
    config['siteFolder'] = config['rootFolder'] + config['siteFolder']


  def tarFiles(self, config, filename, source_folders, type):
    excludeFiles = configuration.getSettings('excludeFiles')
    excludeFiles = excludeFiles[type] if type in excludeFiles else False
    cmd = 'tar'
    if excludeFiles:
      print excludeFiles
      cmd += ' --exclude="'  + '" --exclude="'.join(excludeFiles) + '"'
    cmd += ' -czPf ' + filename
    cmd += ' ' + ' '.join(source_folders)
    self.run_quietly(cmd)

  def backup(self, config, **kwargs):
    self.setRunLocally(config)
    if 'withFiles' in kwargs and kwargs['withFiles'] != True:
      return

    baseName = kwargs['baseName']
    filename = config['backupFolder'] + "/" + '--'.join(baseName) + ".tgz"
    source_folders = kwargs['sourceFolders'] if 'sourceFolders' in kwargs else []

    if 'filesFolder' in config:
      source_folders.append(config['filesFolder'])
    if 'privateFilesFolder' in config:
      source_folders.append(config['privateFilesFolder'])

    if len(source_folders) > 0:
      self.tarFiles(config, filename, source_folders, 'backup')
      print green('Files dumped into "%s"' % filename)

  def listBackups(self, config, results, **kwargs):
    files = self.list_remote_files(config['backupFolder'], ['*.tgz'])
    for file in files:
      hash = re.sub('\.tgz$', '', file)
      backup_result = self.get_backup_result(config, file, hash, 'files')
      if backup_result:
        results.append(backup_result)

  def restore(self, config, files=False, cleanupBeforeRestore=False, **kwargs):
    self.setRunLocally(config)

    file = self.get_backup_result_for_method(files, 'files')
    if not file:
      return

    # move current files folder to backup
    ts = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
    old_files_folder = config['filesFolder'] + '.' + ts + '.old'
    with warn_only():
      self.run_quietly('chmod u+w ' + os.path.dirname(config['filesFolder']))
      self.run_quietly('chmod -R u+x '+config['filesFolder'])
      self.run_quietly('rm -rf '+ old_files_folder)
      self.run_quietly('mv ' + config['filesFolder'] + ' '+old_files_folder)

    tar_file = config['backupFolder'] + '/' + file['file']
    self.run_quietly('mkdir -p ' + config['filesFolder'])
    self.run_quietly('chmod -R 777 ' + config['filesFolder'])
    with cd(config['filesFolder']):
      self.run_quietly('tar -xzPf ' + tar_file, 'Unpacking files')

    print(green('files restored from ' + file['file']))

  def rsync(self, source_config, target_config, folder = 'filesFolder'):
    if not target_config['supportsCopyFrom']:
      print red('The configuration "{c} does not support copyFrom'.format(c=source_config['config_name']))
      return

    print green('Copying files from {f} to {t}'.format(f=source_config['config_name'], t=target_config['config_name']))


    with cd(env.config['rootFolder']):
      exclude_settings = configuration.getSettings('excludeFiles')
      exclude_files_setting = exclude_settings['copyFrom']
      rsync_args = ''
      if exclude_files_setting:
        rsync_args = ' --exclude "' + '" --exclude "'.join(exclude_files_setting) + '"'


      rsync = 'rsync -rav --no-o --no-g  -e "ssh -T -o Compression=no {ssh_args} -p {port}" {rsync_args} {user}@{host}:{source_dir}/* {target_dir}'.format(
        ssh_args=utils.ssh_no_strict_key_host_checking_params,
        source_dir=source_config[folder],
        target_dir=target_config[folder],
        rsync_args=rsync_args,
        **source_config
      )

      with warn_only():
        run(rsync)

  def put(self, config, filename):
    put(filename, config['tmpFolder'])

  def get(self, config, remotePath, localPath):
    if 'runLocally' in config:
      local('cp %s %s' % (remotePath, localPath))
      return

    if (exists(remotePath)):
      get(remotePath, localPath)
    else:
      print red("Could not find file '%s' on remote!" % remotePath)

  def copyFilesFrom(self, config, source_config=False, **kwargs):
    self.setRunLocally(config)
    keys = ['filesFolder', 'privateFilesFolder']
    for key in keys:
      if key in source_config and key in config:
        self.rsync(source_config, config, key)
