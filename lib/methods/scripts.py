import logging
log = logging.getLogger('fabric.fabalicious.scripts')

from base import BaseMethod
from fabric.api import *
from fabric.contrib.files import exists
from fabric.network import *
from fabric.context_managers import settings as _settings
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

  def cd(self, folder, runLocally):
    if runLocally:
      return lcd(folder)
    else:
      return cd(folder)

  def runScriptImpl(self, rootFolder, commands, config, runLocally, callbacks= {}, environment = {}, replacements = {}):

    pattern = re.compile('\%(\S*)\%')
    state = {
      'warnOnly': False,
      'config': config,
      'return_code': 0,
      'runLocally': runLocally
    }

    # preflight
    ok = True
    for line in commands:
      if pattern.search(line) != None:
        log.error('Found replacement-pattern in script-line "%s", aborting ...' % line)
        ok = False

    for key in environment:
      if pattern.search(environment[key]) != None:
        log.error('Found replacement-pattern in environment "%s:%s", aborting ...' % (key, environment[key]))
        ok = False

    if not ok:
      self.printReplacements(replacements)
      exit(1)

    saved_output_prefix = env.output_prefix
    env.output_prefix = False

    for line in commands:
      with self.cd(rootFolder, runLocally), shell_env(**environment), hide('running'), show('output'):
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

            log.debug('Executing "%s"' % func_name)
            if arguments:
              callbacks[func_name](state, *arguments)
            else:
              callbacks[func_name](state)
            handled = True

        if not handled:
          line = self.expandCommand(line)
          log.debug('Running "%s"' % line)
          if state['warnOnly']:
            with warn_only():
              result = local(line) if runLocally else run(line)
              state['return_code'] = state['return_code'] or result.return_code
          else:
            result = local(line) if runLocally else run(line)
            state['return_code'] = state['return_code'] or result.return_code

    env.output_prefix = saved_output_prefix

    return state['return_code']


  def expandEnvironment(self, environment, replacements):
    parsed_environment = {}
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    for key in environment:
      parsed_environment[key] = pattern.sub(lambda x: replacements[x.group()], environment[key])

    return parsed_environment


  def executeCallback(self, context, command, *args, **kwargs):
    config = context['config']
    if not config['runsLocally']:
      host_string = join_host_strings(config['user'], config['host'], config['port'])
      kwargs['host'] = host_string
    execute(command, *args, **kwargs)

  def runTaskCallback(self, context, *args, **kwargs):
    log.error('run_task is not supported anymore, use "execute(docker, <your_task>)"');

  def failOnErrorCallback(self, context, flag):
    if flag == '1':
      context['warnOnly'] = False
    else:
      context['warnOnly'] = True

  def failOnMissingDirectory(self, context, directory, message):
    folder_exists = True
    if context['runLocally']:
      folder_exists = os.path.exists(directory)
    else:
      folder_exists = exists(directory)

    if not folder_exists:
      log.error(message)
      log.error('Missing: %s' % directory)
      exit(1);


  def runScript(self, config, **kwargs):
    self.setRunLocally(config)

    script = kwargs['script']
    callbacks = kwargs['callbacks'] if 'callbacks' in kwargs else {}
    variables = kwargs['variables'] if 'variables' in kwargs else {}
    environment = kwargs['environment'] if 'environment' in kwargs else {}
    root_folder = kwargs['rootFolder'] if 'rootFolder' in kwargs else config['siteFolder'] if 'siteFolder' in config else '.'
    runLocally = kwargs['runLocally'] if 'runLocally' in kwargs else self.run_locally

    if 'environment' in config:
      environment = configuration.data_merge(config['environment'], environment)
    variables['host'] = config
    settings = copy.deepcopy(configuration.getSettings())
    map(lambda x: settings.pop(x,None), ['hosts', 'dockerHosts'])
    variables['settings'] = settings

    callbacks['execute'] = self.executeCallback
    callbacks['run_task'] = self.runTaskCallback
    callbacks['fail_on_error'] = self.failOnErrorCallback
    callbacks['fail_on_missing_directory'] = self.failOnMissingDirectory

    replacements = self.expandVariables(variables);
    commands = self.expandCommands(script, replacements)
    # Do it again to support replacements which needs to be replaced again.
    commands = self.expandCommands(commands, replacements)
    environment = self.expandEnvironment(environment, replacements)


    for need in config['needs']:
      environment[need.upper() + '_AVAILABLE'] = "1"

    return_code = self.runScriptImpl(root_folder, commands, config, runLocally, callbacks, environment, replacements)
    if return_code:
      log.error('Due to earlier errors quitting now.')
      exit(return_code)

  def runTaskSpecificScript(self, taskName, config, **kwargs):
    common_scripts = configuration.getSettings('common')
    type = config['type']

    if type in common_scripts and isinstance(common_scripts[type], list):
      log.error("Found old-style common-scripts. Please regroup by common > taskName > type > commands.")

    if taskName in common_scripts:
      if type in common_scripts[taskName]:
        script = common_scripts[taskName][type]
        log.info('Running common script for task %s and type %s' % (taskName, type))
        self.runScript(config, script=script)

    if taskName in config:
      script = config[taskName]
      log.info('Running host-script for task %s and type %s' % (taskName, type))
      self.runScript(config, script=script)

  def fallback(self, taskName, configuration, **kwargs):
    self.runTaskSpecificScript(taskName, configuration, **kwargs)

  def preflight(self, taskName, configuration, **kwargs):
    self.runTaskSpecificScript(taskName + "Prepare", configuration, **kwargs)


  def postflight(self, taskName, configuration, **kwargs):
    self.runTaskSpecificScript(taskName + "Finished", configuration, **kwargs)
