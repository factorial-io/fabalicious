import logging
log = logging.getLogger('fabric.fabalicious.foo')
from yapsy.IPlugin import IPlugin


from fabric.api import *
from fabric.tasks import Task

class Foo(Task, IPlugin):
  aliases = ['foo','foobar']
  def run(self):
    log.info('Foobar runs...')
