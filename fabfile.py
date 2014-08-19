from fabric.api import *
from fabric.colors import green, red
import datetime
import yaml

settings = 0
current_config = 'unknown'

env.forward_agent = True


def get_all_configurations():
  stream = open("fabfile.yaml", 'r')
  return yaml.load(stream)


def get_configuration(name):
  config = get_all_configurations()
  if name in config['hosts']:
    global settings
    settings = config

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
    if 'ignoreSubmodules' not in host_config:
      host_config['ignoreSubmodules'] = False

    return host_config

  print(red('Configuraton '+name+' not found'))
  exit()

def apply_config(config, name):

  if 'port' in config:
    env.port = config['port']
  if 'password' in config:
    env.password = config['password']

  env.user = config['user']
  env.hosts = [ config['host'] ]
  env.config = config

  global current_config
  current_config = name


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

def get_settings(key, subkey):
  if key in settings:
    if subkey in settings[key]:
      return settings[key][subkey]

  return False



def header():
 print(green("Huber\'s Deployment Scripts\n"))

def check_source_config(config_name = False):
  check_config()

  if not config_name:
    print(red('copyFrom needs a configuration as a source to copy from'))
    exit()

  source_config = get_configuration(config_name)
  if not source_config:
    print(red('can\'t find source config '+config_name))
    exit();

  return source_config


def get_version():
  with cd(env.config['rootFolder']):
    with hide('output'):
      output = run('git describe --always')

      return output.stdout.strip().replace('/','-')


def get_backup_file_name(config, config_name):
  i = datetime.datetime.now()
  return config['backupFolder'] + "/" +get_version()+ '--' + config_name + "--"+i.strftime('%Y-%m-%d--%H-%M-%S')

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
  apply_config(config, config_name)


@task
def uname():
  check_config()
  run('uname -a')


@task
def reset():
  check_config()
  print green('Resetting '+ settings['name'] + "@" + current_config)

  if env.config['hasDrush'] == True:
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        if env.config['useForDevelopment'] == True:
          run('drush user-password admin --password="admin"')
          run('chmod -R 777 ' + env.config['filesFolder'])

        run('drush en -y ' + settings['deploymentModule'])
        run('drush fra -y')
        run('drush updb -y')
        run('drush  cc all')

  run_custom(env.config, 'reset')



def backup_sql(backup_file_name, config):
  if(env.config['hasDrush']):
    with cd(config['siteFolder']):
      with shell_env(COLUMNS='72'):
        run('mkdir -p ' + config['backupFolder'])
        run('drush sql-dump > ' + backup_file_name)



@task
def backup(withFiles=True):
  check_config()

  print green('backing up files and database of ' + settings['name'] + "@" + current_config)


  exclude_files_setting = get_settings('excludeFiles', 'backup')
  exclude_files_str = ''
  if exclude_files_setting:
    exclude_files_str = ' --exclude="' + '" --exclude="'.join(exclude_files_setting) + '"'

  backup_file_name = get_backup_file_name(env.config, current_config)
  backup_sql(backup_file_name+'.sql', env.config)

  if withFiles and withFiles != '0':
    with cd(env.config['filesFolder']):
      run('tar '+exclude_files_str+' -czPf ' + backup_file_name + '.tgz *')
  else:
    print "Backup of files skipped per request..."

  run_custom(env.config, 'backup')



@task
def deploy():

  check_config()
  branch = env.config['branch']

  if not env.config['useForDevelopment']:
    backup_file_name = get_backup_file_name(env.config, current_config)
    print green('backing up DB of ' + settings['name'] + '@' + current_config+ ' to '+backup_file_name+'.sql')
    backup_sql(backup_file_name+'.sql', env.config)

  print green('Deploying branch '+ branch + " to " + settings['name'] + "@" + current_config)

  run_custom(env.config, 'deployPrepare')
  
  with cd(env.config['rootFolder']):
    run('git fetch --tags')
    run('git pull origin '+branch)
    if not env.config['ignoreSubmodules']:
      run('git submodule update')

  run_custom(env.config, 'deploy')

  reset()





@task
def version():
  print green(settings['name'] + ' @ ' + current_config+' tagged with: ' + get_version())

@task
def copyFilesFrom(config_name = False):
  source_config = check_source_config(config_name)
  print green('Copying files from '+ config_name + " to " + current_config)

  source_ssh_port = '22'
  if 'port' in source_config:
    source_ssh_port = source_config['port']

  with cd(env.config['rootFolder']):
    exclude_files_setting = get_settings('excludeFiles', 'copyFrom')
    exclude_files_str = ''
    if exclude_files_setting:
      exclude_files_str = ' --exclude "' + '" --exclude "'.join(exclude_files_setting) + '"'


    rsync = 'rsync -rav ';
    rsync += ' -e "ssh -p '+str(source_ssh_port)+'"'
    rsync += ' ' + exclude_files_str
    rsync += ' ' + source_config['user']+'@'+source_config['host']
    rsync += ':' + source_config['filesFolder']+'/*'
    rsync += ' '
    rsync += env.config['filesFolder']
    run(rsync)


@task
def copyDbFrom(config_name):
  source_config = check_source_config(config_name)
  print green('Copying database from '+ config_name + " to " + current_config)

  if(env.config['hasDrush']):

    source_ssh_port = '22'
    if 'port' in source_config:
      source_ssh_port = source_config['port']

    ssh_args = ' ' + source_config['user']+'@'+source_config['host']

    sql_name = '/tmp/' + config_name + '.sql'

    # create sql-dump on source
    execute(backup_sql, sql_name, source_config, host=source_config['user']+'@'+source_config['host']+':'+str(source_ssh_port))

    # copy sql to target
    run('scp -P '+str(source_ssh_port)+' '+ssh_args+':'+sql_name+' '+sql_name+ ' >>/dev/null')
    run('ssh -p '+str(source_ssh_port)+' '+ssh_args+' rm ' + sql_name)

    # import sql into target
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        run('$(drush sql-connect) < ' + sql_name)
        run('rm '+sql_name)


@task
def copyFrom(config_name = False):
  copyFilesFrom(config_name)
  copyDbFrom(config_name)
  reset()

@task
def drush(drush_command):
  check_config()
  if (env.config['hasDrush']):
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        run('drush '+drush_command)
