import logging
log = logging.getLogger('fabric.fabalicious.foo')
from lib.plugins.task import ITaskPlugin

class Foo(ITaskPlugin):
  aliases = ['foo','foobar']
  def run(self):
    log.info('Foobar runs...')
