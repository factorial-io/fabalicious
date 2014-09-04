from fabric.api import *
from fabric.colors import green, red
import datetime
import yaml
import subprocess, shlex, atexit, time

settings = 0
current_config = 'unknown'

env.forward_agent = True

class SSHTunnel:
  def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, timeout=15):
    self.local_port = local_port
    cmd = 'ssh -vAN -L %d:%s:%d %s@%s' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    atexit.register(self.p.kill)
    while not 'Entering interactive session' in self.p.stderr.readline():
      if time.time() > start_time + timeout:
        raise "SSH tunnel timed out"
  def entrance(self):
    return 'localhost:%d' % self.local_port


def get_all_configurations():
  stream = open("fabfile.yaml", 'r')
  return yaml.load(stream)


def get_configuration(name):
  config = get_all_configurations()
  if name in config['hosts']:
    global settings
    settings = config
    if not 'common' in settings:
      settings['common'] = { }

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

    if 'supportsBackups' not in host_config:
      host_config['supportsBackups'] = True

    if 'supportsCopyFrom' not in host_config:
      host_config['supportsCopyFrom'] = True

    if 'supportsInstalls' not in host_config:
      host_config['supportsInstalls'] = True

    if 'supportsZippedBackups' not in host_config:
      host_config['supportsZippedBackups'] = True

    return host_config

  print(red('Configuraton '+name+' not found'))
  exit()

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

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

  if 'sshTunnel' in config:
    o = config['sshTunnel']
    if 'destHostFromDockerContainer' in o:
      cmd = 'ssh -p %d %s@%s docker inspect %s | grep IPAddress' % (o['bridgePort'], o['bridgeUser'], o['bridgeHost'], o['destHostFromDockerContainer'])

      output = local(cmd, capture=True)
      ip_address = find_between(output.stdout, '"IPAddress": "', '"')
      print "Docker container " + o['destHostFromDockerContainer'] + " uses IP " + ip_address

      o['destHost'] = ip_address

    tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'])


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


def runCommonCommands():
  key = 'development' if env.config['useForDevelopment'] else 'deployment'
  if key in settings['common']:
    for line in settings['common'][key]:
      run(line)


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
      print(key.ljust(25) + ': '+ str(value))


@task
def config(config_name='local'):
  config = get_configuration(config_name)
  apply_config(config, config_name)


@task
def uname():
  check_config()
  run('uname -a')


@task
def reset(withPasswordReset=False):
  check_config()
  print green('Resetting '+ settings['name'] + "@" + current_config)

  if env.config['hasDrush'] == True:
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        if env.config['useForDevelopment'] == True:
          if withPasswordReset in [True, 'True', '1']:
            run('drush user-password admin --password="admin"')
          run('chmod -R 777 ' + env.config['filesFolder'])
        if 'deploymentModule' in settings:
          run('drush en -y ' + settings['deploymentModule'])
        run('drush fra -y')
        run('drush updb -y')
        runCommonCommands()
        run('drush  cc all')

  run_custom(env.config, 'reset')



def backup_sql(backup_file_name, config):
  if(env.config['hasDrush']):
    with cd(config['siteFolder']):
      with shell_env(COLUMNS='72'):
        with warn_only():
          run('mkdir -p ' + config['backupFolder'])
          if config['supportsZippedBackups']:
            run('drush sql-dump --gzip --result-file=' + backup_file_name)
          else:
            run('drush sql-dump --result-file=' + backup_file_name)



@task
def backup(withFiles=True):
  check_config()
  if not env.config['supportsBackups']:
    return

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

  if not env.config['useForDevelopment'] and env.config['supportsBackups']:
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

  if not env.config['supportsCopyFrom']:
    return

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

    with warn_only():
      run(rsync)


@task
def copyDbFrom(config_name):
  source_config = check_source_config(config_name)

  if not env.config['supportsCopyFrom']:
    return

  print green('Copying database from '+ config_name + " to " + current_config)

  if(env.config['hasDrush']):

    source_ssh_port = '22'
    if 'port' in source_config:
      source_ssh_port = source_config['port']

    ssh_args = ' ' + source_config['user']+'@'+source_config['host']

    sql_name = '/tmp/' + config_name + '.sql'


    # create sql-dump on source
    execute(backup_sql, sql_name, source_config, host=source_config['user']+'@'+source_config['host']+':'+str(source_ssh_port))

    if source_config['supportsZippedBackups']:
      sql_name += '.gz'


    # copy sql to target
    run('scp -P '+str(source_ssh_port)+' '+ssh_args+':'+sql_name+' '+sql_name+ ' >>/dev/null')
    run('ssh -p '+str(source_ssh_port)+' '+ssh_args+' rm ' + sql_name)

    # import sql into target
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        if source_config['supportsZippedBackups']:
          run('zcat '+ sql_name + ' | $(drush sql-connect)')
        else:
          run('$(drush sql-connect) < ' + sql_name)

        run('rm '+sql_name)


@task
def copyFrom(config_name = False):
  copyFilesFrom(config_name)
  copyDbFrom(config_name)
  reset(withPasswordReset=True)

@task
def drush(drush_command):
  check_config()
  if (env.config['hasDrush']):
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        run('drush '+drush_command)

@task
def install():
  check_config()
  if env.config['hasDrush'] and env.config['useForDevelopment'] and env.config['supportsInstalls']:
    if 'databaseName' not in env.config:
      print red('missing databaseName in config '+current_config)
      exit()

    print green('Installing fresh database for '+ current_config)

    databaseName = env.config['databaseName']
    with cd(env.config['siteFolder']):
      with shell_env(COLUMNS='72'):
        run('mysql -u root --password=vagrant -e "create database if not exists '+databaseName+'";')
        with warn_only():
          run('chmod u+w '+env.config['siteFolder'])
          run('chmod u+w '+env.config['siteFolder']+'/settings.php')
          run('rm '+env.config['siteFolder']+'/settings.php.old')
          run('mv '+env.config['siteFolder']+'/settings.php '+env.config['siteFolder']+'/settings.php.old')

          run('drush site-install minimal  --site-name="'+settings['name']+'" --account-name=admin --account-pass=admin --db-url=mysql://root:vagrant@localhost/'+databaseName)

        if 'deploymentModule' in settings:
          run('drush en '+settings['deploymentModule'])
