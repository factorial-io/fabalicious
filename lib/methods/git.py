from base import BaseMethod
from fabric.api import *

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




