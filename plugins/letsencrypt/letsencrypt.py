import logging
log = logging.getLogger('fabric.fabalicious.letsencrypt')
from lib.plugins.task import ITaskPlugin
from lib.plugins.method import IMethodPlugin

from fabric.api import *
from lib import configuration
from lib.utils import validate_dict
from lib.configuration import data_merge

class LetsEncryptMethod(IMethodPlugin):
  @staticmethod
  def supports(methodName):
    return methodName == 'letsencrypt'

  @staticmethod
  def validateConfig(config):
    if 'letsencrypt' not in config:
      return validate_dict(['letsencrypt'], config)

    return validate_dict(['domains'], config['letsencrypt'], 'letsencrypt')

  def installDependencies(self):
    with warn_only(), hide('warnings', 'running', 'output'):
      result = self.run('which certbot', capture = True)
      if (result.return_code == 0):
        return

    execute('script', scriptKey='installCertbot')

  def letsencrypt(self, config, **kwargs):
    self.setRunLocally(config)
    self.installDependencies()

    args = {}
    args['webroot'] = config['rootFolder']
    args['domains'] = ' -d '.join(config['letsencrypt']['domains'])

    self.run('certbot certonly --webroot -w {webroot} -d {domains}'.format(**args))

    execute('docker', command='stop');
    execute('docker', command='start');


class LetsEncryptTask(ITaskPlugin):

  def run(what):

    from lib import methods

    configuration.check()
    methods.runTask(configuration.current(), 'letsencrypt', what=what)
