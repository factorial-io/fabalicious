from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
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
    baseName = kwargs['baseName']
    filename = config['backupFolder'] + "/" + '--'.join(baseName) + ".tgz"
    source_folders = kwargs['sourceFolders'] if 'sourceFolders' in kwargs else []
    source_folders.append(config['filesFolder'])
    if 'privateFilesFolder' in config:
      source_folders.append(config['privateFilesFolder'])


    self.tarFiles(config, filename, source_folders, 'backup')
    print green('Files dumped into "%s"' % filename)

