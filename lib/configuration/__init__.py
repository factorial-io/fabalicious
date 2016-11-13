from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red, yellow
import os.path
import urllib2
import yaml
import copy
import hashlib
import sys

fabalicious_version = '2.0.3'

settings = 0
verbose_output = False
current_config = 'unknown'

env.forward_agent = True
env.use_shell = False

fabfile_basedir = False


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
      print red('Could not read from %s' % file)
      print red(e)
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
    data['hosts'] = load_all_yamls_from_dir(path + "/hosts")
    data['dockerHosts'] = load_all_yamls_from_dir(path + "/dockerHosts")

  data = resolve_inheritance(data, {})
  if 'requires' in data:
    check_fabalicious_version(data['requires'], 'file ' + input_file)

  override_filename = find_configfiles(['fabfile.local.yaml'], 3)
  if override_filename:
    print yellow('Using overrides from %s' % override_filename)
    override_data = yaml.load(open(override_filename, 'r'))
    data = data_merge(data, override_data)

  return data


def get_all_configurations():
  global fabfile_basedir
  # Find our configuration-file:
  candidates = ['fabfile.yaml', 'fabalicious/index.yaml', 'fabfile.yaml.inc']

  config_file_name = find_configfiles(candidates, 3)
  if (config_file_name):
    fabfile_basedir = os.path.dirname(config_file_name)
    try:
      return load_configuration(config_file_name)
    except IOError:
      print "could not read from %s " % (config_file_name)
  else:
    print red('could not find suitable configuration file!')

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


def validate_dict(keys, dict, message):
  validated = True
  for key in keys:
    if key not in dict:
      print(red(message + ' ' + key))
      validated = False

  if not validated:
    exit(1)



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
    print red('The %s needs %s as minimum app-version.' % (msg, required_version))
    print red('You are currently using %s. Please update your fabalicious installation.' % current_version)
    exit(1)



def get_configuration(name):
  unsupported = {
    'needsComposer': '"%s" is unsupported, please add "composer" to your "needs" ',
    'hasDrush': '"%s" is unsupported, please add "drush7" or "drush8" to your "needs"',
    'supportsSSH': '"%s" is unsupported, please add "ssh" to your "needs"',
    'useForDevelopment': '"%s" is unsupported, please use "type" with "dev|prod|stage" as value.'
  }

  config = get_all_configurations()
  if name in config['hosts']:
    global settings
    settings = config
    if not 'common' in settings:
      settings['common'] = { }

    if not "usePty" in settings:
      settings['usePty'] = True

    if not "useShell" in settings:
      settings['useShell'] = True

    if not "disableKnownHosts" in settings:
      settings['disableKnownHosts'] = False

    if not "gitOptions" in settings:
      settings['gitOptions'] = { 'pull' : [ '--no-edit', '--rebase'] }

    if not 'sqlSkipTables' in settings:
      settings['sqlSkipTables'] = [
        'cache',
        'cache_block',
        'cache_bootstrap',
        'cache_field',
        'cache_filter',
        'cache_form',
        'cache_menu',
        'cache_page',
        'cache_path',
        'cache_update',
        'cache_views',
        'cache_views_data',
      ]

    if not 'slack' in settings:
      settings['slack'] = {}
    settings['slack'] = data_merge( { 'notifyOn': [], 'username': 'Fabalicious', 'icon_emoji': ':tada:'}, settings['slack'])

    if 'needs' not in settings:
      settings['needs'] = ['ssh', 'git', 'drush7', 'files']

    if 'scripts' not in settings:
      settings['scripts'] = {}

    if 'configurationManagement' not in settings:
      settings['configurationManagement'] = [ 'staging' ];


    host_config = config['hosts'][name]
    host_config = resolve_inheritance(host_config, config['hosts'])

    if 'requires' in host_config:
      check_fabalicious_version(host_config['requires'], 'host-configuration ' + name)

    keys = ("host", "rootFolder")
    validate_dict(keys, host_config, 'Configuraton '+name+' has missing key')

    # add defaults
    defaults = {
      'port': 22,
      'type': 'prod',
      'ignoreSubmodules': False,
      'supportsBackups': True,
      'supportsCopyFrom': True,
      'supportsInstalls': False,
      'supportsZippedBackups': True,
      'tmpFolder': '/tmp/',
      'gitRootFolder': host_config['rootFolder'],
      'gitOptions': settings['gitOptions'],
      'branch': 'master',
      'useShell': settings['useShell'],
      'disableKnownHosts': settings['disableKnownHosts'],
      'usePty': settings['usePty'],
      'needs': settings['needs'],
      'scripts': {},
      'slack': {},
      'configurationManagement': settings['configurationManagement'],
    }

    for key in defaults:
      if key not in host_config:
        host_config[key] = defaults[key]

    # check keys again
    if 'ssh' in host_config['needs']:
      keys = ("rootFolder", "filesFolder", "siteFolder", "backupFolder", "branch")
      validate_dict(keys, host_config, 'Configuraton '+name+' has missing key')

      host_config['siteFolder'] = host_config['rootFolder'] + host_config['siteFolder']
      host_config['filesFolder'] = host_config['rootFolder'] + host_config['filesFolder']

      host_config['gitOptions'] = data_merge(settings['gitOptions'], host_config['gitOptions'])

    else:
      # disable other settings, when ssh is not available
      keys = ( 'ignoreSubmodules', 'supportsBackups', 'supportsCopyFrom', 'supportsInstalls')
      for key in keys:
        host_config[key] = False

    if "docker" in host_config:
      keys = ("name", "configuration")
      validate_dict(keys, host_config["docker"], 'Configuraton '+name+' has missing key in docker')
      if not 'tag' in host_config["docker"]:
        host_config["docker"]["tag"] = "latest"

    if "sshTunnel" in host_config and "docker" in host_config:
      docker_name = host_config["docker"]["name"]
      host_config["sshTunnel"]["destHostFromDockerContainer"] = docker_name

    if "sshTunnel" in host_config:
      if not 'localPort' in host_config['sshTunnel']:
        host_config['sshTunnel']['localPort'] = host_config['port']

    if "behatPath" in host_config:
      host_config['behat'] = { 'presets': dict() }
      host_config['behat']['run'] = host_config['behatPath']

    if not 'behat' in host_config:
      host_config['behat'] = { 'presets': dict() }

    host_config['slack'] = data_merge(settings['slack'], host_config['slack'])

    if 'database' in host_config:
      if 'host' not in host_config['database']:
        host_config['database']['host'] = 'localhost'

    if not 'backupBeforeDeploy' in host_config:
      host_config['backupBeforeDeploy'] = host_config['type'] != 'dev'

    config['needs'].append('script')


    host_config['config_name'] = name

    for key in unsupported:
      if key in host_config:
        print red(unsupported[key] % key)

    return host_config

  print(red('Configuraton '+name+' not found \n'))
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
    print red("could not find configuration %s" % config_file_name)
    for candidate in candidates:
      print red("- tried: %s" % candidate)

    return False

  data = False
  # print "Reading configuration from %s" % found
  try:
    stream = open(found, 'r')
    data = yaml.load(stream)
  except IOError:
    print red("could not read configuration from %s" % found)

  return data

def remote_config_cache_get_filename(config_file_name):
  m = hashlib.md5()
  m.update(config_file_name);
  filename = os.path.expanduser("~") + "/.fabalicious/" + m.hexdigest() + '.yaml'
  if not os.path.exists(os.path.dirname(filename)):
    os.makedirs(os.path.dirname(filename))

  return filename

def remote_config_cache_save(config_file_name, data):
  filename = remote_config_cache_get_filename(config_file_name)
  stream = open(filename, 'w')
  yaml.dump(data, stream, default_flow_style=False)

def remote_config_cache_load(config_file_name):
  try:
    filename = remote_config_cache_get_filename(config_file_name)
    stream = open(filename, 'r')
    data = yaml.load(stream)
    return data
  except:
    return False


def get_configuration_via_http(config_file_name):
  try:
    # print "Reading configuration from %s" % config_file_name
    response = urllib2.urlopen(config_file_name)
    html = response.read()
    data = yaml.load(html)
    remote_config_cache_save(config_file_name, data)
    return yaml.load(html)
  except (urllib2.URLError, urllib2.HTTPError) as err:
    data = remote_config_cache_load(config_file_name)
    if data:
      print yellow('Could not read configuration from %s, using cached data.' % config_file_name)
      return data

    print red('Could not read/find configuration from %s' % config_file_name)

  return False


def apply(config, name):

  env.config = config

  global current_config
  current_config = name

  env.use_shell = config['useShell']
  env.always_use_pty = config['usePty']
  env.disable_known_hosts = config['disableKnownHosts']

  # print "use_shell: %i, use_pty: %i" % (env.use_shell, env.always_use_pty)

  if 'ssh' not in config['needs']:
    return;

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
          print red('Config "%s" does not support method "%s"' % (env.config['config_name'], ', '.join(methods)))
          exit(1)
      return True
    else:
      return True

  print(red('no config set! Please use fab config:<your-config> <task>'))
  exit(1)


def get(name):
  return get_configuration(name)

def current(key = False):
  if key:
    return env.config[key]
  else:
    return env.config

def getAll():
  return get_all_configurations()

def getSettings(key = False, defaultValue = False):
  if key:
    return settings[key] if key in settings else defaultValue
  else:
    return settings


def getBaseDir():
  global fabfile_basedir
  return fabfile_basedir

