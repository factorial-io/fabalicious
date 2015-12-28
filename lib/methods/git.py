from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red

class GitMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'git'

  def getVersion(self, config):
    with cd(config['gitRootFolder']):
      with hide('output', 'running'):
        output = run('git describe --always')
        output = output.stdout.splitlines()
        result = output[-1].replace('/', '-')
        return result

  def getCommitHash(self, config):
    with cd(config['gitRootFolder']):
      with hide('output', 'running'):
        output = run('git rev-parse HEAD')
        output = output.stdout.splitlines()
        result = output[-1].replace('/', '-')
        return result


  def backupPrepare(self, config, **kwargs):
    version = self.getVersion(config)
    # inject version to basename.
    kwargs['baseName'].insert(1, version)


  def cleanWorkingCopy(self):
    with hide('running', 'output', 'warnings'), warn_only():
      result = run('git diff --exit-code --quiet')
      return result.return_code == 0


  def deploy(self, config, **kwargs):

    branch = config['branch']

    with cd(env.config['gitRootFolder']):

      if not self.cleanWorkingCopy():
        print red("Working copy is not clean, aborting.\n")
        run('git status')
        exit(1)

      # run not quietly to see ssh-warnings, -confirms
      run('git fetch -q origin')
      run('git checkout ' + branch)
      run('git fetch --tags')

      git_options = ''
      if 'pull' in env.config['gitOptions']:
        git_options = ' '.join(env.config['gitOptions']['pull'])

      run('git pull -q '+ git_options + ' origin ' + branch)

      if not env.config['ignoreSubmodules']:
        run('git submodule init')
        run('git submodule sync')
        run('git submodule update --init --recursive')

    fn = self.factory.get('script', 'runTaskSpecificScript')
    fn('deploy', config, **kwargs)

  def restore(self, config, files=False, cleanupBeforeRestore=False, **kwargs):

    commit = False
    for file in files:
      if 'commit' in file and len(file['commit']) > 0:
        commit = file['commit']

    if commit:
      run('git checkout ' + commit)
      print(green('source restored to ' + commit))

