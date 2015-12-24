from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red
import os.path
import urllib2
import yaml
import copy
import hashlib

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

  if os.path.splitext(input_file)[1] == '.lock':
    return data;

  # create one big data-object

  if 'dockerHosts' in data:
    for config_name in data['dockerHosts']:
      host = data['dockerHosts'][config_name]
      host = resolve_inheritance(host, data['dockerHosts'])
      data['dockerHosts'][config_name] = host
      if 'requires' in host:
        check_fabalicious_version(host['requires'], 'docker-configuration ' + config_name)

  global settings
  settings = data
  if 'hosts' in data:
    for config_name in data['hosts']:
      host = data['hosts'][config_name]
      host = resolve_inheritance(host, data['hosts'])
      data['hosts'][config_name] = host

      if 'requires' in host:
        check_fabalicious_version(host['requires'], 'host ' + config_name)

      if 'docker' in host and 'configuration' in host['docker']:
        docker_config_name = host['docker']['configuration']
        new_docker_config_name = hashlib.md5(docker_config_name).hexdigest()

        docker_config = get_docker_configuration(docker_config_name, host)
        if (docker_config):
          data['dockerHosts'][new_docker_config_name] = docker_config
          host['docker']['configuration'] = new_docker_config_name



  output_file_name = os.path.dirname(input_file) + '/fabfile.yaml.lock'
  try:
    with open(output_file_name, 'w') as outfile:
      outfile.write( yaml.dump(data, default_flow_style=False) )
  except IOError as e:
    print "Warning, could not safe fafile.yaml.lock: %s" % e

  # print json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))

  return data

def internet_on():
  try:
    urllib2.urlopen('http://www.google.com',timeout=2)
    return True
  except urllib2.URLError:
    pass

  return False


def get_all_configurations():
  global fabfile_basedir


  if fabfile_basedir:
    start_folder = fabfile_basedir
  else:
    start_folder = os.path.dirname(os.path.realpath(__file__))

  max_levels = 3
  from_cache = False

  # Find our configuration-file:
  candidates = ['fabfile.yaml', 'fabalicious/index.yaml', 'fabfile.yaml.inc']

  if not internet_on():
    print "No internet available, trying to read from lock-file ..."
    candidates = ['fabfile.yaml.lock'] + candidates

  while max_levels >= 0:
    for candidate in candidates:
      try:
        if os.path.isfile(start_folder + '/' + candidate):
          fabfile_basedir = start_folder
          return load_configuration(start_folder + '/' + candidate)

      except IOError:
        print "could not read from %s " % (start_folder + '/' + candidate)

    max_levels = max_levels - 1
    start_folder = os.path.dirname(start_folder)

  # if we get here, we didn't find a suitable configuration file
  print(red('could not find suitable configuration file!'))
  exit(1)



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
    base_config = all_configs[inherits_from]

  if base_config and 'inheritsFrom' in base_config:
    base_config = resolve_inheritance(base_config, all_configs)

  if base_config:
    config = data_merge(base_config, config)

  return config

def versiontuple(v):
  return tuple(map(int, (v.split("."))))

def check_fabalicious_version(required_version, msg):
  required_version = str(required_version)

  if not check_fabalicious_version.version:

    file = __file__
    if os.path.basename(file) == 'fabfile.pyc':
      file = os.path.dirname(file) + '/fabfile.py';

    app_folder = os.path.dirname(os.path.realpath(file))

    with hide('output', 'running'):
      output = local('cd %s; git describe --always' % app_folder, capture=True)
      output = output.stdout.splitlines()
      check_fabalicious_version.version = output[-1].replace('/', '-')
      p = check_fabalicious_version.version.find('-')
      if p >= 0:
        check_fabalicious_version.version = check_fabalicious_version.version[0:p]

  current_version = check_fabalicious_version.version

  if (versiontuple(current_version) < versiontuple(required_version)):
    print red('The %s needs %s as minimum app-version.' % (msg, required_version))
    print red('You are currently using %s. Please update your fabalicious installation.' % current_version)
    exit(1)


check_fabalicious_version.version = False

def get_configuration(name):
  unsupported = {
    'needsComposer': 'Unsupported, please add "composer" to your "needs" ',
    'hasDrush': 'Unsupported, please add "drush7" or "drush8" to your "needs"',
    'supportsSSH': 'Unsupported, please add "ssh" to your "needs"',
    'useForDevelopment': 'Unsupported, please use "type" with dev|prod|stage as value.'
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
      settings['needs'] = ['ssh', 'git', 'drush7']

    if 'scripts' not in settings:
      settings['scripts'] = {}


    host_config = config['hosts'][name]
    if 'requires' in host_config:
      check_fabalicious_version(host_config['requires'], 'host-configuration ' + name)

    keys = ("host", "rootFolder")
    validate_dict(keys, host_config, 'Configuraton '+name+' has missing key')

    # add defaults
    defaults = {
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
      'slack': {}
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


    config['needs'].append('script')


    host_config['config_name'] = name

    for key in unsupported:
      if key in host_config:
        print red(key + ' ' + unsupported[key])

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



def get_configuration_via_http(config_file_name):
  try:
    # print "Reading configuration from %s" % config_file_name
    response = urllib2.urlopen(config_file_name)
    html = response.read()
    return yaml.load(html)
  except urllib2.HTTPError, err:
    if err.code == 404:
      print red('Could not read/find configuration at %s' %config_file_name)
    else:
      raise

  return False



def get_docker_configuration(config_name, config):
  if config_name[0:7] == 'http://' or config_name[0:8] == 'https://':
    data = get_configuration_via_http(config_name)
    return resolve_inheritance(data, {})
  elif config_name[0:1] == '.':
    data = get_configuration_via_file(config_name)
    return resolve_inheritance(data, {})
  else:
    all_docker_hosts = copy.deepcopy(settings['dockerHosts'])
    config_name = config['docker']['configuration']
    if config_name in all_docker_hosts:
      return all_docker_hosts[config_name]

  return False

def create_ssh_tunnel(config, tunnel_config, remote=False):
  o = tunnel_config

  if 'destHostFromDockerContainer' in o:

    ip_address = get_docker_container_ip(o['destHostFromDockerContainer'], o['bridgeHost'], o['bridgeUser'], o['bridgePort'])

    if not ip_address:
      print red('Docker not running, can\'t establish tunnel')
      return

    print(green("Docker container " + o['destHostFromDockerContainer'] + " uses IP " + ip_address))

    o['destHost'] = ip_address

  strictHostKeyChecking = True
  if 'strictHostKeyChecking' in o:
    strictHostKeyChecking = o['strictHostKeyChecking']

  if remote:
    tunnel = RemoteSSHTunnel(config, o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)
  else:
    tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)

  return tunnel




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

  if 'sshTunnel' in config:
    create_ssh_tunnel(config, config['sshTunnel'])

  # add docker configuration password to env.passwords
  if 'docker' in config:

    docker_configuration = get_docker_configuration(config['docker']['configuration'], config)

    if docker_configuration:

      host_str = docker_configuration['user'] + '@'+docker_configuration['host']+':'+str(docker_configuration['port'])

      if 'password' in docker_configuration:
        env.passwords[host_str]= docker_configuration['password']



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

def getSettings(key = False):
  if key:
    return settings[key] if key in settings else False
  else:
    return settings


def getBaseDir():
  global fabfile_basedir
  return fabfile_basedir

