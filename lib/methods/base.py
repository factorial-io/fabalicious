from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red
from fabric.context_managers import env
from fabric.network import *
from fabric.contrib.files import exists
import re


class LocallyContext():
    def __init__(self, parent, config):
      self.parent= parent
      self.config = config

    def __enter__(self):
      self.saved = self.parent.run_locally
      self.parent.setRunLocally(self.config)
      return self

    def __exit__(self, type, value, traceback):
      self.parent.run_locally = self.saved


class BaseMethod(object):

  verbose_output = True
  run_locally = False

  @staticmethod
  def supports(methodName):
    return False

  @staticmethod
  def validateConfig(config):
    return {}

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    pass

  @staticmethod
  def applyConfig(config, settings):
    pass

  @staticmethod
  def addExecutables(config, executables):
    for e in executables:
      if e not in config['executables']:
        config['executables'][e] = e


  def __init__(self, methodName, factory):
    self.methodName = methodName
    self.factory = factory

  @staticmethod
  def getOverrides():
    return False


  def preflight(self, task, config, **kwargs):
    pass


  def postflight(self, task, config, **kwargs):
    pass

  def fallback(self, task, config, **kwargs):
    pass


  def addPasswordToFabricCache(self, user, host, port, password, **kwargs):
    host_string = join_host_strings(user, host, port)
    env.passwords[host_string] = password


  def list_remote_files(self, base_folder, patterns):
    result = []
    with cd(base_folder), hide('running', 'output', 'warnings'), warn_only():
      for pattern in patterns:
        cmd = 'ls -l ' + pattern + ' 2>/dev/null'
        output = run(cmd)
        lines = output.stdout.splitlines()
        for line in lines:
          tokens = line.split()

          if(len(tokens) >= 9):
            result.append(tokens[8])
    return result


  def get_backup_result(self, config, file, hash, method):
    tokens = hash.split('--')
    if len(tokens) < 3:
      return False
    # be backwards compatible.
    if tokens[0] != config['config_name']:
      tokens[0], tokens[1] = tokens[1], tokens[0]

    if tokens[0] != config['config_name']:
      return False
    return {
      'config': tokens[0],
      'commit': tokens[1],
      'date':   tokens[2],
      'time':   tokens[3],
      'method': method,
      'hash':   hash,
      'file':   file
    }


  def get_backup_result_for_method(self, files, method):
    file = filter(lambda f: f['method'] == method, files)
    if len(file) != 1:
      return False
    return file[0]




  def runLocally(self, config):
    return LocallyContext(self, config)

  def setRunLocally(self, config):
    self.run_locally = config['runLocally']
    self.executables = config['executables']

  def cd(self, path):
    # print red('cd: %d %s'% (self.run_locally,  path))
    return lcd(path) if self.run_locally else cd(path)

  def expandCommand(self, cmd):
    if len(self.executables) > 0:
      pattern = re.compile('|'.join(re.escape("#!" + key) for key in self.executables.keys()))
      cmd = pattern.sub(lambda x: self.executables[x.group()[2:]], cmd)

    return cmd

  def run(self, cmd, **kwargs):
    # print red("run: %d %s" % ( self.run_locally, cmd))
    cmd = self.expandCommand(cmd)

    if self.run_locally:
      return local(cmd, **kwargs)
    else:
      if 'capture' in kwargs:
        kwargs.pop('capture')
      return run(cmd, **kwargs)

  def exists(self, fname):
    return os.path.isfile(fname) if self.run_locally else exists(fname)


  def run_quietly(self, cmd, msg = '', hide_output = None, may_fail=False):
    if 'warn_only' in env and env['warn_only']:
      may_fail = True

    if msg != '':
      print msg

    if not hide_output:
      hide_output = ['running', 'output', 'warnings']

    if self.verbose_output:
      hide_output=[]


    with hide(*hide_output):
      try:
        result = self.run(cmd)

        if not may_fail and result.return_code != 0:
          print red('%s failed:' %s)
          print result

        return result
      except:
        print red('%s failed' % cmd)

        if output['aborts']:
          raise SystemExit('%s failed' % cmd);
