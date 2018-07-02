import logging
log = logging.getLogger('fabric.fabalicious.set')
from lib.plugins.task import ITaskPlugin
from lib import configuration

import sys
import os
import subprocess
from multiprocessing import Pool, Lock
from contextlib import contextmanager


globallock = Lock()

@contextmanager
def poolcontext(*args, **kwargs):
    pool = Pool(*args, **kwargs)
    yield pool
    pool.terminate()

def runFabalicious(args):
  config = args.pop(0)
  log.info(config + ": Running " + " ".join(args))
  process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  def check_io():
    captured = ''
    while True:
      output = process.stdout.readline().decode()
      if output:
        captured += output
        log.debug(config + ": " + output.replace("\n", ""))
      else:
        break
    return captured

  # keep checking stdout/stderr until the child exits
  while process.poll() is None:
    captured = check_io()

  # Log the result for humans
  globallock.acquire()
  log.info('')
  log.info(config + ": Results of " + " ".join(args))
  for line in captured.splitlines():
    log.info(config + ": " + line)
  log.info('')
  log.info('')

  globallock.release()


class Set(ITaskPlugin):
  def run(self, *args, **kwargs):
    num_processes = int(kwargs['processes']) if 'processes' in kwargs else 1

    if len(args) < 1:
      log.error('Please provide a list of blueprints or \'all\'')
      exit(1)

    blueprints = configuration.getSettings('blueprints')
    config = configuration.current()
    if not config:
      log.error('set needs a valid configuration!')
      exit(1)

    config_name = configuration.current('config_name')

    found = False
    for b in blueprints:
      if b['configName'] == config_name:
        found = b

    if not found:
      log.error('%s not found in blueprints-section' % config_name)
      exit(1)

    variants = []
    if args[0] == 'all':
      variants = b['variants']
    else:
      for arg in args:
        if arg in b['variants']:
          variants.append(arg)
        else:
          log.error("Could not find variant %s in blueprint.variants" % arg)
          exit(1)

    commands = []
    for variant in variants:
      command = [
        variant,
        sys.argv[0],
        sys.argv[1],
        'blueprint:' + variant
      ]
      command = command + sys.argv[3:]
      commands.append(command)

      log.info(" ".join(command))
    log.info("Using %s parallel processes" % num_processes)
    result = raw_input('Do you want to execute above listed commands? (Y/N) ')

    if (result[:1] != 'y') and (result[:1] != 'Y'):
      exit(0)

    with poolcontext(processes=num_processes) as pool:
      pool.map(runFabalicious, commands)

    exit(0)

