#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.state import output, env
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
  with hide('output', 'running', 'warnings'):
    configuration.check()
    keys = in_key.split('/')
    c = configuration.current()
    for key in keys:
      if key in c:
        c = c[key]
      else:
        print red('property %s not found!' % in_key)
        exit(1)

  print c
  exit(0)


@task
def version():
  configuration.check('git')
  version = methods.call('git', 'getVersion', configuration.current())
  print green('%s @ %s tagged with: %s' % (configuration.getSettings('name'), configuration.current('config_name'), version))

@task
def list():
  config = configuration.getAll()
  print("Found configurations for: "+ config['name']+"\n")
  for key, value in config['hosts'].items():
    print '- ' + key


@task
def reset(**kvargs):
  configuration.check()
  print green('Resetting '+ configuration.getSettings('name') + "@" + configuration.current('config_name'))
  methods.runTask(configuration.current(), 'reset', **kvargs)

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

  file_name = configuration.current('config_name') + "--" + time.strftime("%Y%m%d-%H%M%S") + '.sql'

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

  methods.runTask(configuration.current(), 'backup', withFiles=withFiles, baseName = basename)

