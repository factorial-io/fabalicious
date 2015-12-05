from base import BaseMethod

class GitMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'git'

  def getVersion(config):

    if not config['supportsSSH']:
        return 'unknown';

    with cd(config['gitRootFolder']):
      with hide('output', 'running'):
        output = run('git describe --always')
        output = output.stdout.splitlines()
        return output[-1].replace('/', '-')



