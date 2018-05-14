import logging
log = logging.getLogger('fabric.fabalicious.configuration')

from fabric.api import *
from fabric.state import output, env
import os.path
import urllib2
import yaml
import copy
import glob
import hashlib
import sys
from lib.utils import validate_dict

fabalicious_version = '2.3.0'

root_data = 0
verbose_output = False
current_config = 'unknown'

env.forward_agent = True
env.use_shell = False

fabfile_basedir = False
fabalicious_rootdir = None
offline = False
cache = {}

globalMethodSettings = {}

def load_all_yamls_from_dir(path):
  result = {}
  files = glob.glob(path+'/*.yaml') + glob.glob(path+'/*.yml')

  for file in files:
    try:
      stream = open(file, 'r')
      data = yaml.load(stream)
      key = os.path.basename(file)
      key = os.path.splitext(key)[0]
      result[key] = data

    except IOError as e:
      log.error('Could not read from %s' % file)
      log.error(e)
  return result



def load_configuration(input_file):
  # print "Reading configuration from %s" % input_file

  stream = open(input_file, 'r')
  data = yaml.load(stream)

  if 'hosts' not in data:
    data['hosts'] = {}
  if 'dockerHosts' not in data:
    data['dockerHosts'] = {}

  if (os.path.basename(input_file) == 'index.yaml'):
    path = os.path.dirname(input_file)
    hosts = load_all_yamls_from_dir(path + "/hosts")
    dockerHosts = load_all_yamls_from_dir(path + "/dockerHosts")
    if hosts:
      data['hosts'] = hosts
    if dockerHosts:
      data['dockerHosts'] = dockerHosts

  data = resolve_inheritance(data, {})
  if 'requires' in data:
    check_fabalicious_version(data['requires'], 'file ' + input_file)

  override_filename = find_configfiles(['fabfile.local.yaml'], 3)
  if override_filename:
    log.warning('Using overrides from %s' % override_filename)
    override_data = yaml.load(open(override_filename, 'r'))
    data = data_merge(data, override_data)

  return data


def get_all_configurations():
  global fabfile_basedir
  # Find our configuration-file:
  candidates = ['fabfile.yaml', '.fabfile.yaml', 'fabalicious/index.yaml', '.fabalicious/index.yaml', 'fabfile.yaml.inc']

  config_file_name = find_configfiles(candidates, 3)
  if (config_file_name):
    fabfile_basedir = os.path.dirname(config_file_name)
    try:
      return load_configuration(config_file_name)
    except IOError:
      print "could not read from %s " % (config_file_name)
  else:
    log.error('could not find suitable configuration file!')

  exit(1)

def find_configfiles(candidates, max_levels):
  global fabfile_basedir

  if fabfile_basedir:
    start_folder = fabfile_basedir
  else:
    start_folder = os.path.dirname(os.path.realpath(__file__))

  while max_levels >= 0:
    for candidate in candidates:
      if os.path.isfile(start_folder + '/' + candidate):
        return start_folder + '/' + candidate

    max_levels = max_levels - 1
    start_folder = os.path.dirname(start_folder)

  return False


def data_merge(a, b):
  output = {}
  for item, value in a.iteritems():
    if b.has_key(item):
      if isinstance(b[item], dict):
        output[item] = data_merge(value, b.pop(item))
    else:
      output[item] = copy.deepcopy(value)
  for item, value in b.iteritems():
    output[item] = copy.deepcopy(value)
  return output


def resolve_inheritance(config, all_configs):
  if not config or 'inheritsFrom' not in config:
    return config

  inherits_from = config['inheritsFrom']
  config.pop('inheritsFrom', None)

  if not isinstance(inherits_from, basestring):
    for item in reversed(inherits_from):
      config['inheritsFrom'] = item
      config = resolve_inheritance_impl(config, all_configs)

    return config

  else:
    config['inheritsFrom'] = inherits_from
    return resolve_inheritance_impl(config, all_configs)


def resolve_inheritance_impl(config, all_configs):
  if 'inheritsFrom' not in config:
    return config

  inherits_from = config['inheritsFrom']
  base_config = False

  if inherits_from[0:7] == 'http://' or inherits_from[0:8] == 'https://':
    base_config = get_configuration_via_http(inherits_from)

  elif inherits_from[0:1] == '.' or inherits_from[0:1] == '/':
    base_config = get_configuration_via_file(inherits_from)

  elif inherits_from in all_configs:
    base_config = copy.deepcopy(all_configs[inherits_from])

  if base_config and 'inheritsFrom' in base_config:
    base_config = resolve_inheritance(base_config, all_configs)

  if base_config:
    config = data_merge(base_config, config)

  return config

def versiontuple(v):
  return tuple(map(int, (v.split("."))))

def check_fabalicious_version(required_version, msg):
  required_version = str(required_version)

  current_version = fabalicious_version

  if (versiontuple(current_version) < versiontuple(required_version)):
    log.error('The %s needs %s as minimum app-version.' % (msg, required_version))
    log.error('You are currently using %s. Please update your fabalicious installation.' % current_version)
    exit(1)

def validate_config_against_methods(config):
  from lib import methods

  errors = validate_dict(['rootFolder', 'type', 'needs'], config)
  methodNames = config['needs']
  for methodName in methodNames:
    m = methods.getMethod(methodName)
    e = m.validateConfig(config)
    errors = data_merge(errors, e)

  if len(errors) > 0:
    for key, msg in errors.iteritems():
      log.error('Key \'%s\' in %s: %s' % (key, config['config_name'], msg))

    exit(1)

  if config['rootFolder'][-1:] == '/':
    config['rootFolder'] = config['rootFolder'][:-1]

def get_default_config_from_methods(config, settings, defaults):
  from lib import methods

  methodNames = config['needs']
  for methodName in methodNames:
    m = methods.getMethod(methodName)
    m.getDefaultConfig(config, settings, defaults)

  return defaults

def apply_config_by_methods(config, settings):
  from lib import methods

  methodNames = config['needs']
  for methodName in methodNames:
    m = methods.getMethod(methodName)
    m.applyConfig(config, settings)


def get_configuration(name):
  unsupported = {
    'needsComposer': '"%s" is unsupported, please add "composer" to your "needs" ',
    'hasDrush': '"%s" is unsupported, please add "drush7" or "drush8" to your "needs"',
    'supportsSSH': '"%s" is unsupported, please add "ssh" to your "needs"',
    'useForDevelopment': '"%s" is unsupported, please use "type" with "dev|prod|stage" as value.'
  }
  config = getAll()

  if name in config['hosts']:
    host_config = copy.deepcopy(config['hosts'][name])
    host_config = resolve_inheritance(host_config, config['hosts'])

    if 'requires' in host_config:
      check_fabalicious_version(host_config['requires'], 'host-configuration ' + name)

    if 'needs' not in host_config:
      host_config['needs'] = config['needs']

    if 'runLocally' not in host_config:
      host_config['runLocally'] = False

    if 'script' not in host_config['needs']:
      host_config['needs'].append('script')

    host_config['config_name'] = name

    validate_config_against_methods(host_config)

    # add defaults
    defaults = {
      'type': 'prod',
      'supportsBackups': True,
      'supportsCopyFrom': True,
      'supportsInstalls': False,
      'supportsZippedBackups': True,
      'tmpFolder': '/tmp',
      'scripts': {},
      'executables': config['executables'],
      'runsLocally': False
    }

    defaults = get_default_config_from_methods(host_config, config, defaults)

    for key in defaults:
      if key not in host_config:
        host_config[key] = defaults[key]

    apply_config_by_methods(host_config, config)

    if 'database' in host_config:
      if 'host' not in host_config['database']:
        host_config['database']['host'] = 'localhost'

    if not 'backupBeforeDeploy' in host_config:
      host_config['backupBeforeDeploy'] = host_config['type'] != 'dev' and host_config['type'] != 'test'




    for key in unsupported:
      if key in host_config:
        log.error(unsupported[key] % key)

    return host_config

  log.error('Configuraton '+name+' not found \n')
  list()
  exit(1)

def get_configuration_via_file(config_file_name):
  global fabfile_basedir
  candidates = []
  candidates.append( os.path.abspath(config_file_name) )
  candidates.append( fabfile_basedir + '/' + config_file_name )
  candidates.append( fabfile_basedir + '/fabalicious/' + config_file_name )
  found = False
  for candidate in candidates:
    if os.path.isfile(candidate):
      found = candidate
      break;

  if not found:
    log.error("could not find configuration %s" % config_file_name)
    for candidate in candidates:
      log.error("- tried: %s" % candidate)

    return False

  data = False
  # print "Reading configuration from %s" % found
  try:
    stream = open(found, 'r')
    data = yaml.load(stream)
  except IOError:
    log.error("could not read configuration from %s" % found)

  return data

def remote_config_cache_get_filename(config_file_name, as_yaml):
  m = hashlib.md5()
  m.update(config_file_name);
  filename = os.path.expanduser("~") + "/.fabalicious/" + m.hexdigest()
  filename += '.yaml' if as_yaml else '.data'

  if not os.path.exists(os.path.dirname(filename)):
    os.makedirs(os.path.dirname(filename))

  return filename

def remote_config_cache_save(config_file_name, data, as_yaml):
  filename = remote_config_cache_get_filename(config_file_name, as_yaml)
  stream = open(filename, 'w')
  if as_yaml:
    yaml.dump(data, stream, default_flow_style=False)
  else:
    stream.write(data)

def remote_config_cache_load(config_file_name, as_yaml):
  try:
    filename = remote_config_cache_get_filename(config_file_name, as_yaml)
    stream = open(filename, 'r')
    if as_yaml:
      data = yaml.load(stream)
    else:
      data = stream.read()

    return data
  except:
    return False

def get_configuration_via_http(config_file_name, as_yaml = True):
  if config_file_name not in cache:
    cache[config_file_name] = get_configuration_via_http_impl(config_file_name, as_yaml)

  return cache[config_file_name]

def get_configuration_via_http_impl(config_file_name, as_yaml = True):
  try:
    if offline:
      raise Exception('offline')

    # print "Reading configuration from %s" % config_file_name
    response = urllib2.urlopen(config_file_name)
    html = response.read()
    data = yaml.load(html) if as_yaml else html
    remote_config_cache_save(config_file_name, data, as_yaml)
    return data
  except (Exception, urllib2.URLError, urllib2.HTTPError) as err:
    data = remote_config_cache_load(config_file_name, as_yaml)
    if data:
      if offline:
        log.info('Using cached configuration for %s' % config_file_name)
      else:
        log.warning('Could not read configuration from %s, using cached data.' % config_file_name)

      return data

    log.error('Could not read/find configuration from %s' % config_file_name)

  return False


def apply(config, name):

  env.config = config

  global current_config
  current_config = name

  if 'ssh' not in config['needs']:
    return;

  env.use_shell = config['useShell']
  env.always_use_pty = config['usePty']
  env.disable_known_hosts = config['disableKnownHosts']

  if 'port' in config:
    env.port = config['port']
  if 'password' in config:
    env.password = config['password']

  env.user = config['user']
  env.hosts = [ config['host'] ]




def check(methods= False):
  if 'config' in env:
    if methods:
      found = False
      if isinstance(methods, str):
        methods = [ methods ]
      for method in methods:
        if method in env.config['needs']:
          found = True
      if not found:
          log.error('Config "%s" does not support method "%s"' % (env.config['config_name'], ', '.join(methods)))
          exit(1)
      return True
    else:
      return True

  log.error('no config set! Please use fab config:<your-config> <task>')
  exit(1)


def get(name):
  return get_configuration(name)

def current(key = False):
  if not hasattr(env, 'config'):
    return False

  if key:
    return env.config[key]
  else:
    return env.config

def getAll():
  global root_data
  global globalMethodSettings

  if not root_data:

    root_data = get_all_configurations()
    root_data = data_merge(globalMethodSettings, root_data)

    if not 'common' in root_data:
      root_data['common'] = { }

    if 'needs' not in root_data:
      root_data['needs'] = ['ssh', 'git', 'drush7', 'files']




  return root_data

def getSettings(key = False, defaultValue = False):
  """Helper function to read configuration from fabfiles.
  Allow use of dot operator (".") to get nested value.
  """
  if key is False:
    return getAll()

  settings = defaultValue
  keys = key.split('.')
  firstRunFlag = True
  for key in keys:
    if firstRunFlag:
      firstRunFlag = False
      settings = _getSetting(key, defaultValue)
    else:
      settings = settings[key] if key in settings else defaultValue
  return settings

def _getSetting(key = False, defaultValue = False):
  settings = getAll()
  if key:
    return settings[key] if key in settings else defaultValue
  else:
    return settings

def getBaseDir():
  """Retrieves the directory where fabfile.yaml is located.
  """
  global fabfile_basedir
  return fabfile_basedir

def setRootDir(root_dir):
  """Set the root directory of fabalicious, where fabfile.py is located.
  """
  global fabalicious_rootdir
  fabalicious_rootdir = root_dir

def getRootDir():
  """Retrieves the root directory of fabalicious, where fabfile.py is located.
  """
  global fabalicious_rootdir
  return fabalicious_rootdir

def getDockerConfig(docker_config_name, runLocally = False, printErrors=True):

  settings = getAll()

  if 'dockerHosts' not in settings:
    return False

  dockerHosts = settings['dockerHosts']

  if not dockerHosts or docker_config_name not in dockerHosts:
    return False

  docker_config = copy.deepcopy(dockerHosts[docker_config_name])
  docker_config = resolve_inheritance(docker_config, dockerHosts)

  if 'runLocally' in docker_config and docker_config['runLocally'] or runLocally:
    keys = ['rootFolder', 'tasks']
  else:
    docker_config['runLocally'] = False
    keys = ['tasks', 'rootFolder', 'user', 'host', 'port']

  errors = validate_dict(keys, docker_config)
  if len(errors) > 0:
    if printErrors:
      for key in errors:
        log.error('Missing key \'%s\' in docker-configuration %s' % (key, docker_config_name))

    return False

  return docker_config


def add(config_name, config):
  settings = getAll()
  settings['hosts'][config_name] = config


def addGlobalSettings(data):
  global globalMethodSettings
  global root_data

  if root_data:
    root_data = data_merge(data, root_data)
  else:
    globalMethodSettings = data_merge(globalMethodSettings, data)
