from base import BaseMethod
from fabric.api import *
from fabric.network import *
from fabric.context_managers import settings as _settings
from fabric.colors import green, red
from lib import configuration
import re, copy

class ScriptMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'script'

  def printReplacements(self, replacements):

    for key in sorted(replacements.keys()):
      value = replacements[key]
      print "{key:<40}  |  {value}".format(key = key, value=value)


  def runScriptImpl(self, rootFolder, commands, config, callbacks= {}, environment = {}, replacements = {}):

    pattern = re.compile('\%(\S*)\%')
    state = { 'warnOnly': False, 'config': config }

    # preflight
    ok = True
    for line in commands:
      if pattern.search(line) != None:
        print red('Found replacement-pattern in script-line "%s", aborting ...' % line)
        ok = False

    for key in environment:
      if pattern.search(environment[key]) != None:
        print red('Found replacement-pattern in environment "%s:%s", aborting ...' % (key, environment[key]))
        ok = False

    if not ok:
      self.printReplacements(replacements)
      exit(1)

    saved_output_prefix = env.output_prefix
    env.output_prefix = False

    for line in commands:
      with cd(rootFolder), shell_env(**environment), hide('running'):
        handled = False
        start_p = line.find('(')
        end_p = line.rfind(')')

        if start_p >= 0 and end_p > 0:
          func_name = line[0:start_p]

          if func_name in callbacks:
            arguments = False
            func_args = line[start_p+1: end_p]
            if func_args.strip() != '':
              arguments = func_args.split(',')
              arguments = map(lambda x: x.strip(), arguments)

            if arguments:
              callbacks[func_name](state, *arguments)
            else:
              callbacks[func_name](state)
            handled = True

        if not handled:
          if state['warnOnly']:
            with warn_only():
              run(line)
          else:
            run(line)
    env.output_prefix = saved_output_prefix

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
    for line in commands:
      result = pattern.sub(lambda x: replacements[x.group()], line)
      parsed_commands.append(result)

    return parsed_commands

  def expandEnvironment(self, environment, replacements):
    parsed_environment = {}
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    for key in environment:
      parsed_environment[key] = pattern.sub(lambda x: replacements[x.group()], environment[key])

    return parsed_environment


  def executeCallback(self, context, command, *args, **kwargs):
    config = context['config']
    host_string = join_host_strings(config['user'], config['host'], config['port'])
    print host_string
    kwargs['host'] = host_string
    execute(command, *args, **kwargs)

  def runTaskCallback(self, context, *args, **kwargs):
    print red('run_task is not supported anymore, use "execute(docker, <your_task>)"');

  def failOnErrorCallback(self, context, flag):
    if flag == '1':
      context['warnOnly'] = False
    else:
      context['warnOnly'] = True


  def runScript(self, config, **kwargs):
    script = kwargs['script']
    callbacks = kwargs['callbacks'] if 'callbacks' in kwargs else {}
    variables = kwargs['variables'] if 'variables' in kwargs else {}
    environment = kwargs['environment'] if 'environment' in kwargs else {}
    root_folder = kwargs['rootFolder'] if 'rootFolder' in kwargs else config['siteFolder']
    if 'environment' in config:
      environment = configuration.data_merge(config['environment'], environment)
    variables['host'] = config
    settings = copy.deepcopy(configuration.getSettings())
    map(lambda x: settings.pop(x,None), ['hosts', 'dockerHosts'])
    variables['settings'] = settings

    callbacks['execute'] = self.executeCallback
    callbacks['run_task'] = self.runTaskCallback
    callbacks['fail_on_error'] = self.failOnErrorCallback

    replacements = self.expandVariables(variables);
    commands = self.expandCommands(script, replacements)
    environment = self.expandEnvironment(environment, replacements)

    for need in config['needs']:
      environment[need.upper() + '_AVAILABLE'] = "1"

    self.runScriptImpl(root_folder, commands, config, callbacks, environment, replacements)


  def runTaskSpecificScript(self, taskName, config, **kwargs):
    common_scripts = configuration.getSettings('common')
    type = config['type']

    if type in common_scripts and isinstance(common_scripts[type], list):
      print red("Found old-style common-scripts. Please regroup by common > taskName > type > command > type > commandss.")

    if taskName in common_scripts:
      if type in common_scripts[taskName]:
        script = common_scripts[taskName][type]
        self.runScript(config, script=script)

    if taskName in config:
      script = config[taskName]
      self.runScript(config, script=script)



  def preflight(self, taskName, configuration, **kwargs):
    self.runTaskSpecificScript(taskName + "Prepare", configuration, **kwargs)


  def postflight(self, taskName, configuration, **kwargs):
    self.runTaskSpecificScript(taskName + "Finished", configuration, **kwargs)




