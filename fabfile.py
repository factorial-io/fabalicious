#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import green, red, yellow
from fabric.network import *
from fabric.context_managers import settings as _settings
import os.path
import time
import datetime
import sys

# Import our modules.
root_folder = os.path.dirname(os.path.realpath(os.path.dirname(__file__) + '/fabfile.py'))
sys.path.append(root_folder)
from lib import methods
from lib import configuration
from lib import blueprints

configuration.fabfile_basedir = root_folder


@task
def config(configName='local'):
  c = configuration.get(configName)
  configuration.apply(c, configName)

@task
def blueprint(branch, configName=False, output=False):
  template = blueprints.getTemplate(configName)
  if not template:
    print red('No blueprint found in configuration!')
    print yellow('run via fab blueprint=<identifier>,configNmae=<configName>,output=<bool>')
    exit(1)

  c = blueprints.apply(branch, template)
  if (output):
    blueprints.output(c)
  else:
    configuration.add(c['configName'], c)
    config(c['configName'])

@task
def getProperty(in_key):
  configuration.check()
  with hide('output', 'running', 'warnings'):
    keys = in_key.split('/')
    c = configuration.current()
    for key in keys:
      if key in c:
        c = c[key]
      else:
        print red('property "%s" not found!' % in_key)
        exit(1)

  print c
  exit(0)

def about_helper(key, value, indent):
  print ' '.ljust(indent) + key.ljust(30 - indent),
  if isinstance(value, dict):
    print ""
    for dict_key, dict_value in value.items():
      about_helper(dict_key, dict_value, indent + 2)
  elif hasattr(value, "__len__") and not hasattr(value, 'strip'):
    print ""
    for list_value in value:
      about_helper('', list_value, indent + 2)
  else:
    print(': ' + str(value))


@task
def about(config_name=False):
  if not config_name:
    config = configuration.current()
    config_name = configuration.current('config_name')
  else:
    config = configuration.get(config_name)
  if config:

    additional_info = {}
    methods.runTask(config, 'about', data = additional_info)

    about_helper('Host-configuration for ' + config_name, config, 2)
    for key, val in additional_info.items():
      print ""
      about_helper(key + ' for ' + config_name, val, 2)


@task
def info():
  print green('Fabalicious %s by Factorial.io. MIT Licensed.\n\n' % configuration.fabalicious_version)

@task
def version():
  configuration.check('git')
  version = methods.call('git', 'getVersion', configuration.current())
  print green('%s @ %s tagged with: %s' % (configuration.getSettings('name'), configuration.current('config_name'), version))

@task
def drush(drush_command):
  configuration.check(['drush7', 'drush8'])
  methods.call('drush', 'drush', configuration.current(), command=drush_command)

@task
def drupalconsole(drupal_command):
  configuration.check(['drupalconsole'])
  methods.call('drupalconsole', 'drupalconsole', configuration.current(), command=drupal_command)

@task
def composer(composer_command):
  configuration.check(['composer'])
  methods.call('composer', 'composer', configuration.current(), command=composer_command)


@task
def list():
  config = configuration.getAll()
  print('Found configurations for "%s":' % config['name']+"\n")
  keys = config['hosts']
  keys = sorted(keys)
  for key in keys:
    print '- ' + key

@task
def reset(**kwargs):
  configuration.check()

  methods.runTask(configuration.current(), 'reset', **kwargs)

@task
def ssh():
  configuration.check(['ssh'])
  methods.call('ssh', 'openShell', configuration.current())



@task
def putFile(fileName):
  configuration.check()
  if configuration.current()['runLocally']:
    print red("putFile not supported when 'runLocally' is set!")
    exit(1)

  methods.call('files', 'put', configuration.current(), filename=fileName)

@task
def getFile(remotePath, localPath='./'):
  configuration.check()

  methods.call('files', 'get', configuration.current(), remotePath=remotePath, localPath=localPath)

@task
def getSQLDump():
  configuration.check()

  file_name = '--'.join([configuration.current('config_name'), time.strftime("%Y%m%d-%H%M%S")]) + '.sql'

  print green('Get SQL dump from %s' % configuration.current('config_name'))

  file_name = '/tmp/' + file_name
  methods.runTask(configuration.current(), 'backupSql', backup_file_name = file_name)
  if configuration.current('supportsZippedBackups'):
    file_name += '.gz'
  getFile(file_name)
  if configuration.current()['runLocally']:
    local('rm ' + file_name)
  else:
    run('rm ' + file_name);

@task
def backup(withFiles = True):
  configuration.check()
  print green('backing up files and database of "%s" @ "%s"' % (configuration.getSettings('name'), configuration.current('config_name')))
  i = datetime.datetime.now()
  basename = [
    configuration.current('config_name'),
    i.strftime('%Y-%m-%d--%H-%M-%S')
  ]

  methods.runTask(configuration.current(), 'backup', withFiles = withFiles, baseName = basename)

@task
def backupDB():
  backup(withFiles=False)

@task
def listBackups(commit = False):
  configuration.check()
  results = []
  if commit:
    results = get_backup_files(commit)

    print "\nFound last backup for %s and commit %s:" % (configuration.current('config_name'), commit)
  else:
    methods.runTask(configuration.current(), 'listBackups', results = results)
    results = sorted(results, key = lambda l: (l['date'], l['time']))
    print "\nFound backups for "+ configuration.current('config_name') + ":"
  last_date = ''
  for result in results:
    if result['date'] == last_date:
      result['date'] = '          '
    else:
      last_date = result['date']

    print "{date} {time}  |  {commit:<30}  |  {method:<10}  |  {file}".format(**result)

def get_backup_files(commit):
  results = []
  methods.runTask(configuration.current(), 'listBackups', results = results)
  results = sorted(results, key = lambda l: (l['date'], l['time']))
  # get latest hash for commit.
  hash = False
  for result in results:
    if result['commit'] == commit:
      hash = result['hash']

  # search for hash.
  if not hash:
    for result in results:
      if result['hash'] == commit:
        hash = result['hash']

  if not hash:
    print red('Coud not find requested backup: %s' % commit)
    listBackups()
    exit()
  else:
    return filter(lambda r: r['hash'] == hash, results)

@task
def getBackup(commit):
  configuration.check()
  files = get_backup_files(commit)
  for file in files:
    remotePath = configuration.current('backupFolder') + "/" + file['file']
    localPath = './' + file['file']

    get(remote_path=remotePath, local_path=localPath)

@task
def restore(commit, cleanupBeforeRestore=0):
  configuration.check()
  files = get_backup_files(commit)
  methods.runTask(configuration.current(), 'restore', files = files, cleanupBeforeRestore = cleanupBeforeRestore)

  reset()

@task
def script(scriptKey = False, *args, **kwargs):
  configuration.check()
  scripts = configuration.current('scripts')
  scriptData = scripts[scriptKey] if scriptKey in scripts else False

  if not scriptData:
    scripts = configuration.getSettings('scripts')
    scriptData = scripts[scriptKey] if scriptKey in scripts else False

  if not scriptData:
    print red('Could not find any script named "%s" in fabfile.yaml' % scriptKey)
    if configuration.current('scripts'):
      print 'Available scripts in %s:\n  - ' % configuration.current('config_name') + '\n  - '.join(configuration.current('scripts').keys())

    if configuration.getSettings('scripts'):
      print 'Available scripts: \n  - '  + '\n  - '.join(configuration.getSettings('scripts').keys())

    exit(1)

  if isinstance(scriptData, dict):
    if 'defaults' in scriptData:
      kwargs = configuration.data_merge(scriptData['defaults'], kwargs)

    scriptData = scriptData['script']

  # compute arguments:
  arguments = ' '.join(args)
  for key in kwargs.keys():
    arguments += ' ' + key + '="' + kwargs[key]+'"'
  variables = {
    'arguments': kwargs,
  }
  variables['arguments']['combined'] = arguments


  if scriptData:
    methods.call('script', 'runScript', configuration.current(), script=scriptData, variables=variables)

@task
def docker(command = False, **kwargs):
  configuration.check()
  methods.call('docker', 'runCommand', configuration.current(), command = command, **kwargs)

@task
def deploy(overrideBranch=False):
  configuration.check()
  config = configuration.current()
  if overrideBranch:
    config['branch'] = overrideBranch

  if config['backupBeforeDeploy']:
      backup(withFiles=False)

  methods.runTask(config, 'deploy', nextTasks=['reset'])


@task
def notify(message):
  configuration.check()
  methods.runTask(configuration.current(), 'notify', message=message)

@task
def copyFilesFrom(source_config_name):
  configuration.check()
  source_configuration = configuration.get(source_config_name)
  methods.runTask(configuration.current(), 'copyFilesFrom', source_config=source_configuration)

@task
def copyDBFrom(source_config_name):
  configuration.check()
  source_configuration = configuration.get(source_config_name)
  methods.runTask(configuration.current(), 'copyDBFrom', source_config=source_configuration, nextTasks=['reset'])


@task
def copyFrom(source_config_name):
  configuration.check()
  copyDBFrom(source_config_name)
  copyFilesFrom(source_config_name)

@task
def restoreSQLFromFile(full_file_name):
  configuration.check()
  methods.runTask(configuration.current(), 'restoreSQLFromFile', sourceFile = full_file_name)

@task
def install(**kwargs):
  configuration.check()
  config = configuration.current()
  if config['type'] == 'prod' or not config['supportsInstalls']:
    print red('Task install is not supported for this configuration. Please check if "type" and "supportsInstalls" is set correctly.')
    exit(1)

  methods.runTask(configuration.current(), 'install', nextTasks=['reset'], **kwargs)


@task
def createApp(**kwargs):
  configuration.check(['docker'])
  stages = [
    {
      'stage': 'checkExistingInstallation',
      'connection': 'docker',
      'context': {
        'installationExists': False
        }
    }
  ]
  createDestroyHelper(stages, 'createApp')
  if stages[0]['context']['installationExists']:
    print green('Found an existing installaion, running deploy instead!')
    deploy()
    return

  # Install the app.
  stages = configuration.getSettings('createAppStages', [
    { 'stage': 'installCode','connection': 'docker' },
    { 'stage': 'installDependencies','connection': 'docker' },
    { 'stage': 'spinUp','connection': 'docker' },
    { 'stage': 'install','connection': 'ssh' },
  ])

  createDestroyHelper(stages, 'createApp', **kwargs)


@task
def destroyApp(**kwargs):
  configuration.check(['docker'])
  stages = configuration.getSettings('destroyAppStages', [
    { 'stage': 'spinDown','connection': 'docker' },
    { 'stage': 'deleteContainer','connection': 'docker' },
    { 'stage': 'deleteCode','connection': 'docker' },
  ])

  createDestroyHelper(stages, 'destroyApp', **kwargs)


def createDestroyHelper(stages, command, **kwargs):

  dockerConfig = configuration.getDockerConfig(configuration.current()['docker']['configuration'])

  for step in stages:
    step['dockerConfig'] = dockerConfig
    print yellow(command + ': current stage: \'{stage}\' via \'{connection}\''.format(**step))

    hostConfig = {}
    for key in ['host', 'user', 'port']:
      hostConfig[key] = configuration.current()[key],

    methods.call(step['connection'], 'getHostConfig', configuration.current(), hostConfig=hostConfig)
    hostString = join_host_strings(**hostConfig)
    with _settings(host_string = hostString):
      methods.runTask(configuration.current(), command, quiet=True, **step)


@task
def updateApp(**kwargs):
  configuration.check()
  config = configuration.current()
  if config['type'] != 'dev':
    print red('Task updateApp is not supported for this configuration. Please check if "type" is set correctly.')
    exit(1)
  backupDB()
  methods.runTask(configuration.current(), 'updateApp', **kwargs)

@task
def doctor(**kwargs):
  configuration.check()
  methods.runTask(configuration.current(), 'doctor', **kwargs)
