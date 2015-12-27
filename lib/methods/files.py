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
      tokens = hash.split('--')
      results.append({
        'config': tokens[0],
        'commit': tokens[1],
        'date':   tokens[2],
        'time':   tokens[3],
        'method': 'files',
        'hash':   hash,
        'file':   file
      })

