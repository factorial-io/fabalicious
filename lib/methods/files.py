from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
import datetime
import os.path
from lib import configuration

class FilesMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'files'

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
      hash = file.split('.')[0]
      results.append(self.get_backup_result(config, file, hash, 'files'))

  def restore(self, config, files=False, cleanupBeforeRestore=False, **kwargs):

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

