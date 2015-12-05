#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red
import os.path
import sys

# Import or modules.
root_folder = os.path.dirname(os.path.realpath(__file__))
sys.path.append(root_folder)
from lib import methods
from lib import configuration


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
  methods.call('git', 'getVersion', configuration.current())
