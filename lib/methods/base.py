import logging
log = logging.getLogger('fabric.fabalicious.base')

from fabric.api import *
from fabric.state import output, env
from fabric.context_managers import env
from fabric.network import *
from fabric.contrib.files import exists

from lib import configuration
from lib import utils

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

  def expandConfig(self, config, settings):
    replacements = {
      'host': config,
      'settings': settings,
      'fabfile': {
        'baseDir': configuration.getBaseDir()
      }
    }
    replacements = self.expandVariables(replacements)
    self.expandConfigImpl(config, replacements)

  def expandConfigImpl(self, data, replacements):
    for key in data:
      if isinstance(data[key], dict):
        self.expandConfigImpl(data[key], replacements)
      elif isinstance(data[key], list):
        pass # lists are not supported.
      elif isinstance(data[key], basestring):
        data[key] = self.expandCommands([data[key]], replacements)[0]


  @staticmethod
  def getGlobalSettings():
    return {}

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


  def expandVariablesImpl(self, prefix, variables, result):
    for key in variables:
      if isinstance(variables[key], dict):
        self.expandVariablesImpl(prefix + "." + key, variables[key], result)
      elif isinstance(variables[key], list):
        pass # lists are not supported.
      else:
        result["%" + prefix + "." + key + "%"] = str(variables[key])

  def expandVariables(self, variables):
    results = {}
    for key in variables:
      self.expandVariablesImpl(key, variables[key], results)

    return results


  def expandCommands(self, commands, replacements):
    parsed_commands = []
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    if commands:
      for line in commands:
        result = pattern.sub(lambda x: replacements[x.group()], line)
        parsed_commands.append(result)
    return parsed_commands

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
    self.setExecutables(config)

  def setExecutables(self, config):

    self.executables = {}
    replacements = self.expandVariables({ "host": config })
    for key, command in config['executables'].iteritems():
      cmds = [ command ];
      cmds = self.expandCommands(cmds, replacements)
      self.executables[key] = cmds[0]



  def cd(self, path):
    # log.error('cd: %d %s'% (self.run_locally,  path))
    return lcd(path) if self.run_locally else cd(path)

  def expandCommand(self, in_cmd):
    cmd = in_cmd
    if len(self.executables) > 0:
      pattern = re.compile('|'.join(re.escape("#!" + key)+"\s" for key in self.executables.keys()))
      cmd = pattern.sub(lambda x: self.executables[x.group()[2:-1]] + ' ', cmd)
      pattern = re.compile('|'.join(re.escape("$$" + key)+"\s" for key in self.executables.keys()))
      cmd = pattern.sub(lambda x: self.executables[x.group()[2:-1]] + ' ', cmd)
      if cmd.find('%arguments%') >= 0:
        arr = in_cmd.split(' ')
        command = arr.pop(0)
        arguments = ' '.join(arr)
        command = command.replace('#!', '');
        cmd = self.executables[command].replace('%arguments%', arguments)

    return cmd

  def run(self, cmd, **kwargs):
    log.debug("run: %d %s" % ( self.run_locally, cmd))
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
          log.error('%s failed:' %s)
          print result

        return result
      except:
        log.error('%s failed' % cmd)

        if output['aborts']:
          raise SystemExit('%s failed' % cmd);


  def getFile(self, source_config, source_file, dest_file, run_locally):

    self.setExecutables(source_config)

    args = utils.ssh_no_strict_key_host_checking_params

    cmd = '#!scp -P {port} {args} {user}@{host}:{source_file} {dest_file} '.format(  args=args,
      source_file=source_file,
      dest_file=dest_file,
      **source_config
      )

    run_locally_saved = self.run_locally
    self.run_locally = run_locally or self.run_locally
    self.run(cmd)
    self.run_locally = run_locally_saved

  def putFile(self, source_file, config, dest_file, run_locally):

    self.setExecutables(config)

    args = utils.ssh_no_strict_key_host_checking_params

    cmd = '#!scp -P {port} {args} {source_file} {user}@{host}:{dest_file} '.format(  args=args,
      source_file=source_file,
      dest_file=dest_file,
      **config
      )

    run_locally_saved = self.run_locally
    self.run_locally = run_locally or self.run_locally
    self.run(cmd)
    self.run_locally = run_locally_saved