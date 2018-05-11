import logging
log = logging.getLogger('fabalicious.git')

from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
from lib.utils import validate_dict
from lib.configuration import data_merge
from lib import configuration

class GitMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'git'

  @staticmethod
  def validateConfig(config):
    return validate_dict(['branch'], config)

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    defaults['gitRootFolder'] = config['rootFolder']
    defaults['ignoreSubmodules'] = False
    defaults['gitOptions'] = {}

  @staticmethod
  def applyConfig(config, settings):
    config['gitOptions'] = data_merge(settings['gitOptions'], config['gitOptions'])
    BaseMethod.addExecutables(config, ['git'])


  def getVersion(self, config):

    with self.runLocally(config), self.cd(config['gitRootFolder']):
      with hide('output', 'running'):
        output = self.run('#!git describe --always', capture = True)
        output = output.stdout.splitlines()
        result = output[-1].replace('/', '-')
        return result

  def getCommitHash(self, config):
    with self.runLocally(config), self.cd(config['gitRootFolder']):
      with hide('output', 'running'):
        output = self.run('#!git rev-parse HEAD', capture=True)
        output = output.stdout.splitlines()
        result = output[-1].replace('/', '-')
        return result


  def backupPrepare(self, config, **kwargs):
    version = self.getVersion(config)
    # inject version to basename.
    kwargs['baseName'].insert(1, version)


  def cleanWorkingCopy(self):
    with hide('running', 'output', 'warnings'), warn_only():
      result = self.run('#!git diff --exit-code --quiet', capture = True)
      return result.return_code == 0


  def deploy(self, config, **kwargs):

    branch = config['branch']

    with self.runLocally(config), self.cd(config['gitRootFolder']):

      if not self.cleanWorkingCopy():
        log.error("Working copy is not clean, aborting.\n")
        self.run('#!git status')
        exit(1)

      # run not quietly to see ssh-warnings, -confirms
      self.run('#!git fetch -q origin')
      self.run('#!git checkout ' + branch)
      self.run('#!git fetch --tags')

      git_options = ''
      if 'pull' in config['gitOptions']:
        git_options = ' '.join(config['gitOptions']['pull'])

      self.run('#!git pull -q '+ git_options + ' origin ' + branch)

      if not config['ignoreSubmodules']:
        self.run('#!git submodule init')
        self.run('#!git submodule sync')
        self.run('#!git submodule update --init --recursive')

    fn = self.factory.get('script', 'runTaskSpecificScript')
    fn('deploy', config, **kwargs)

  def restore(self, config, files=False, cleanupBeforeRestore=False, **kwargs):

    commit = False
    for file in files:
      if 'commit' in file and len(file['commit']) > 0:
        commit = file['commit']

    if commit:
      with self.runLocally(config):
        self.run('#!git checkout ' + commit)
        print(green('source restored to ' + commit))


  def createApp(self, config, stage, dockerConfig, **kwargs):
    targetPath = dockerConfig['rootFolder'] + '/' + config['docker']['projectFolder']
    self.setExecutables(config)

    if (stage == 'checkExistingInstallation'):
      kwargs['context']['installationExists'] = False
      if (self.exists(targetPath + '/.projectCreated')):
        kwargs['context']['installationExists'] = True

      return


    if (stage == 'installCode'):
      repository = False
      if 'docker' in config and 'repository' in config['docker']:
        repository = config['docker']['repository']
      elif 'repository' in config:
        repository = config['repository']
      else:
        repository = configuration.getSettings('repository')

      if not repository:
        log.error('Could not find \'repository\' in host configuration nor in settings')
        exit(1)

      if (self.exists(targetPath + '/.projectCreated')):
        log.info('Application already installed!');
        with self.cd(targetPath):
          self.run('#!git checkout %s' % config['branch'])
          self.run('#!git pull -q origin %s' % config['branch'])
      else:
        self.run('#!git clone -b %s %s %s' % (config['branch'], repository, targetPath))

      with self.cd(targetPath):
        self.run('#!git submodule update --init')
        self.run('touch .projectCreated')


  def destroyApp(self, config, stage, dockerConfig, **kwargs):
    if (stage == 'deleteCode'):
      targetPath = dockerConfig['rootFolder'] + '/' + config['docker']['projectFolder']
      sudo('rm -rf %s' % targetPath, shell=False)
