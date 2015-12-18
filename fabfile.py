#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import green, red
import os.path
import time
import datetime
import sys

# Import or modules.
root_folder = os.path.dirname(os.path.realpath(__file__))
sys.path.append(root_folder)
from lib import methods
from lib import configuration

configuration.fabfile_basedir = root_folder

@task
def config(configName='local'):
  c = configuration.get(configName)
  configuration.apply(c, configName)

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
  print green('Resetting %s @ %s' % (configuration.getSettings('name'), configuration.current('config_name')))
  methods.runTask(configuration.current(), 'reset', **kwargs)

@task
def ssh():
  configuration.check()
  with cd(configuration.current('rootFolder')):
    open_shell()

@task
def putFile(fileName):
  configuration.check()
  put(fileName, configuration.current('tmpFolder'))

@task
def getFile(remotePath, localPath='./'):
  configuration.check()
  get(remote_path=remotePath, local_path=localPath)

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
def script(scriptKey = False):
  configuration.check()
  if scriptKey in configuration.current('scripts'):
    methods.call('script', 'runScript', configuration.current(), script = configuration.current('scripts')[scriptKey])
  elif scriptKey in configuration.getSettings('scripts'):
    methods.call('script', 'runScript', configuration.current(), script = configuration.getSettings('scripts')[scriptKey])
  else:
    print red('Could not find any script named "%s" in fabfile.yaml' % scriptKey)
    exit(1)


@task
def docker(command = False):
  configuration.check()
  methods.call('docker', 'runCommand', configuration.current(), command = command)



