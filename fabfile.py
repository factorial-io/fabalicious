from fabric.api import *
from fabric.colors import green, red
import datetime
import yaml

settings = 0


def get_all_configurations():
  stream = open("fabfile.yaml", 'r')
  return yaml.load(stream)


def get_configuration(name):
  config = get_all_configurations()
  if name in config['hosts']:
    global settings
    settings = config
    settings['currentConfig'] = name

    host_config = config['hosts'][name]
    keys = ("host", "rootFolder", "filesFolder", "siteFolder", "backupFolder", "branch")
    validated = True
    for key in keys:
      if key not in host_config:
        print(red('Configuraton '+name+' has missing key '+key))
        validated = False

    if not validated:
      exit()


    host_config['siteFolder'] = host_config['rootFolder'] + host_config['siteFolder']
    host_config['filesFolder'] = host_config['rootFolder'] + host_config['filesFolder']

    if 'useForDevelopment' not in host_config:
      host_config['useForDevelopment'] = False
    if 'hasDrush' not in host_config:
      host_config['hasDrush'] = False

    return host_config

  print(red('Configuraton '+name+' not found'))
  exit()

def apply_config(config):

  if 'port' in config:
    env.port = config['port']
  if 'password' in config:
    env.password = config['password']

  env.user = config['user']
  env.hosts = [ config['host'] ]
  env.config = config


def check_config():
  if 'config' in env:
    return True

  print(red('no config set! Please use fab config:<your-config> <task>'))
  exit()


def run_custom(config, key):
  if key in config:
    with cd(config['rootFolder']):
      for line in config[key]:
        run(line)


def header():
 print(green("Huber\'s Deployment Scripts\n"))



@task
def list():
  header()
  config = get_all_configurations()
  print("Found configurations for: "+ config['name']+"\n")
  for key, value in config['hosts'].items():
    print '- ' + key


@task
def about(config_name='local'):
  header()
  configuration = get_configuration(config_name)
  if configuration:
    print("Configuration for " + config_name)
    for key, value in configuration.items():
      print(key.ljust(15) + ': '+ value)


@task
def config(config_name='local'):
  config = get_configuration(config_name)
  apply_config(config)


@task
def uname():
  check_config()
  run('uname -a')


@task
def reset():
  check_config()
  print 'Resetting '+ settings['name'] + "@" + settings['currentConfig']
  print 'working in ' + env.config['siteFolder']

  if env.config['hasDrush'] == True:
    with cd(env.config['siteFolder']):
      if env.config['useForDevelopment'] == True:
        run('drush user-password admin --password="admin"')
        run('chmod -R 777 ' + env.config['filesFolder'])

      run('drush -y en ' + settings['deploymentModule'])
      run('drush -y fra')
      run('drush -y updb')
      run('drush  cc all')

  run_custom(env.config, 'reset')



@task
def backup():
  check_config()
  if(env.config['hasDrush']):

    i = datetime.datetime.now()

    backup_file_name = env.config['backupFolder'] + "/" + settings['currentConfig']+ "--"+i.strftime('%Y-%m-%d--%H-%M-%S')

    with cd(env.config['filesFolder']):
      run('mkdir -p ' + env.config['backupFolder'])
      run('drush sql-dump > ' + backup_file_name + '.sql')
      run('tar -czPf ' + backup_file_name + '.tgz *')


  run_custom(env.config, 'backup')

@task
def deploy():

  check_config()
  branch = env.config['branch']

  print 'Deploying branch '+ branch + " to " + settings['name'] + "@" + settings['currentConfig']

  with cd(env.config['rootFolder']):
    run('git pull origin '+branch)
    run('git submodule update')

  reset()

