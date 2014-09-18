#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fabric.api import *
from fabric.colors import green, red
import datetime
import yaml
import subprocess, shlex, atexit, time
import os.path

settings = 0
current_config = 'unknown'

env.forward_agent = True
env.use_shell = False

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


class RemoteSSHTunnel:
  def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, timeout=15):
    self.local_port = local_port
    self.bridge_host = bridge_host
    self.bridge_user = bridge_user

    cmd = 'ssh -L %d:%s:%d %s@%s -f -N -M -S ~/.ssh-tunnel-from-fabric' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
    run(cmd)

    start_time = time.time()

  def entrance(self):
    return 'localhost:%d' % self.local_port

  def kill(self):
    print "killing remote ssh-tunnel"
    cmd = 'ssh -S ~/.ssh-tunnel-from-fabric -O exit %s@%s' % (self.bridge_user, self.bridge_host)
    run(cmd)

def get_all_configurations():

  start_folder = os.path.dirname(os.path.realpath(__file__))
  found = False
  max_levels = 3
  stream = False
  while not found and max_levels >= 0:
    try:
      stream = open(start_folder + "/fabfile.yaml", 'r')
      found = True
    except IOError:
      max_levels = max_levels - 1
      found = False
      start_folder = os.path.dirname(start_folder)

  if not stream:
    print(red('could not find fabfile.yaml'))
    exit()

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
      host_config['supportsInstalls'] = False

    if 'supportsZippedBackups' not in host_config:
      host_config['supportsZippedBackups'] = True

    if 'gitRootFolder' not in host_config:
      host_config['gitRootFolder'] = host_config['rootFolder']

    if 'tmpFolder' not in host_config:
      host_config['tmpFolder'] = '/tmp/'


    return host_config

  print(red('Configuraton '+name+' not found \n'))
  list()
  exit()

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""


def create_ssh_tunnel(o, remote=False):
  if 'destHostFromDockerContainer' in o:
    cmd = 'ssh -p %d %s@%s docker inspect %s | grep IPAddress' % (o['bridgePort'], o['bridgeUser'], o['bridgeHost'], o['destHostFromDockerContainer'])

    output = local(cmd, capture=True)
    ip_address = find_between(output.stdout, '"IPAddress": "', '"')
    print "Docker container " + o['destHostFromDockerContainer'] + " uses IP " + ip_address

    o['destHost'] = ip_address
  if remote:
    tunnel = RemoteSSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'])
  else:
    tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'])

  return tunnel

def apply_config(config, name):

  header()

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
    create_ssh_tunnel(config['sshTunnel'])


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
  if header.sended not in locals() and header.sended != 1:
    print(green("Huber\'s Deployment Scripts\n"))
    header.sended = 1
header.sended = 0


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
  with cd(env.config['gitRootFolder']):
    with hide('output'):
      output = run('git describe --always')

      return output.stdout.strip().replace('/','-')


def get_backup_file_name(config, config_name):
  i = datetime.datetime.now()
  return config['backupFolder'] + "/" +get_version()+ '--' + config_name + "--"+i.strftime('%Y-%m-%d--%H-%M-%S')


def run_common_commands():
  key = 'development' if env.config['useForDevelopment'] else 'deployment'
  if key in settings['common']:
    for line in settings['common'][key]:
      run(line)


def run_drush(cmd, expand_command = True):
  env.output_prefix = False
  if expand_command:
    cmd = 'drush ' + cmd
  run(cmd)
  env.output_prefix = True


@task
def list():
  config = get_all_configurations()
  print("Found configurations for: "+ config['name']+"\n")
  for key, value in config['hosts'].items():
    print '- ' + key


@task
def about(config_name='local'):
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
        if env.config['useForDevelopment'] == True:
          if withPasswordReset in [True, 'True', '1']:
            run_drush('user-password admin --password="admin"')
          run('chmod -R 777 ' + env.config['filesFolder'])
        if 'deploymentModule' in settings:
          run_drush('en -y ' + settings['deploymentModule'])
        run_drush('fra -y')
        run_drush('updb -y')
        run_common_commands()
        run_drush(' cc all')

  run_custom(env.config, 'reset')



def backup_sql(backup_file_name, config):
  print env.host
  if(config['hasDrush']):
    with cd(config['siteFolder']):
      with warn_only():
        run('mkdir -p ' + config['backupFolder'])
        if config['supportsZippedBackups']:
          run_drush('sql-dump --gzip --result-file=' + backup_file_name)
        else:
          run_drush('sql-dump --result-file=' + backup_file_name)



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
    if 'privateFilesFolder' in env.config:
      with cd(env.config['privateFilesFolder']):
        run('tar '+exclude_files_str+' -czPf ' + backup_file_name + '_private.tgz *')
  else:
    print "Backup of files skipped per request..."

  run_custom(env.config, 'backup')



@task
def deploy(resetAfterwards=True):

  check_config()
  branch = env.config['branch']

  if not env.config['useForDevelopment'] and env.config['supportsBackups']:
    backup_file_name = get_backup_file_name(env.config, current_config)
    print green('backing up DB of ' + settings['name'] + '@' + current_config+ ' to '+backup_file_name+'.sql')
    backup_sql(backup_file_name+'.sql', env.config)

  print green('Deploying branch '+ branch + " to " + settings['name'] + "@" + current_config)

  run_custom(env.config, 'deployPrepare')

  with cd(env.config['gitRootFolder']):
    run('git checkout '+branch)
    run('git fetch --tags')
    run('git pull origin '+branch)
    if not env.config['ignoreSubmodules']:
      run('git submodule update')

  run_custom(env.config, 'deploy')

  if resetAfterwards and resetAfterwards != '0':
    reset()





@task
def version():
  print green(settings['name'] + ' @ ' + current_config+' tagged with: ' + get_version())


def rsync(config_name, files_type = 'filesFolder'):

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


    rsync = 'rsync -rav --no-o --no-g ';
    rsync += ' -e "ssh -p '+str(source_ssh_port)+'"'
    rsync += ' ' + exclude_files_str
    rsync += ' ' + source_config['user']+'@'+source_config['host']
    rsync += ':' + source_config[files_type]+'/*'
    rsync += ' '
    rsync += env.config[files_type]

    with warn_only():
      run(rsync)

@task
def copyFilesFrom(config_name = False):
  rsync(config_name)
  source_config = check_source_config(config_name)
  if 'privateFilesFolder' in env.config and 'privateFilesFolder' in source_config:
    rsync(source_config, 'privateFilesFolder')


@task
def copyDbFrom(config_name = False):
  source_config = check_source_config(config_name)
  target_config = check_source_config(current_config)

  if not env.config['supportsCopyFrom']:
    return

  print green('Copying database from '+ config_name + " to " + current_config)

  if(env.config['hasDrush']):

    source_ssh_port = '22'
    if 'port' in source_config:
      source_ssh_port = source_config['port']

    ssh_args = ' ' + source_config['user']+'@'+source_config['host']

    sql_name_source = source_config['tmpFolder'] + config_name + '.sql'
    sql_name_target = target_config['tmpFolder'] + config_name + '.sql'

    # drush has no predictable behaviour
    if source_config['supportsZippedBackups']:
      sql_name_source += '.gz'
      sql_name_target += '.gz'

    # create sql-dump on source
    execute(backup_sql, sql_name_source, source_config, host=source_config['user']+'@'+source_config['host']+':'+str(source_ssh_port))


    # copy sql to target
    run('scp -P '+str(source_ssh_port)+' '+ssh_args+':'+sql_name_source+' '+sql_name_target+ ' >>/dev/null')
    # cleanup and remove file from source
    run('ssh -p '+str(source_ssh_port)+' '+ssh_args+' rm ' + sql_name_source)

    # import sql into target
    with cd(env.config['siteFolder']):
      if source_config['supportsZippedBackups']:
        run_drush('zcat '+ sql_name_target + ' | $(drush sql-connect)', False)
      else:
        run_drush('drush sql-cli < ' + sql_name, False)

      run('rm '+sql_name_target)


@task
def copyFrom(config_name = False):
  source_config = check_source_config(config_name)
  remote_tunnel = False
  if 'sshTunnel' in source_config:
    remote_tunnel = create_ssh_tunnel(source_config['sshTunnel'], True)
    tunnel = create_ssh_tunnel(source_config['sshTunnel'], False)

  try:
    copyFilesFrom(config_name)
    copyDbFrom(config_name)

  finally:
    if remote_tunnel:
      remote_tunnel.kill()

  reset(withPasswordReset=True)


@task
def drush(drush_command):
  check_config()
  if (env.config['hasDrush']):
    with cd(env.config['siteFolder']):
      run_drush(drush_command)

@task
def install():
  check_config()
  if env.config['hasDrush'] and env.config['useForDevelopment'] and env.config['supportsInstalls']:
    if 'database' not in env.config:
      print red('missing database-dictionary in config '+current_config)
      exit()

    print green('Installing fresh database for '+ current_config)

    o = env.config['database']
    run('mkdir -p '+env.config['siteFolder'])
    with cd(env.config['siteFolder']):
      mysql_cmd  = 'CREATE DATABASE IF NOT EXISTS '+o['name']+'; '
      mysql_cmd += 'GRANT ALL PRIVILEGES ON drupal.* TO drupal@localhost IDENTIFIED BY \''+o['pass']+'\'; FLUSH PRIVILEGES;'

      run('mysql -u '+o['user']+' --password='+o['pass']+' -e "'+mysql_cmd+'"')
      with warn_only():
        run('chmod u+w '+env.config['siteFolder'])
        run('chmod u+w '+env.config['siteFolder']+'/settings.php')
        run('rm '+env.config['siteFolder']+'/settings.php.old')
        run('mv '+env.config['siteFolder']+'/settings.php '+env.config['siteFolder']+'/settings.php.old')
        sites_folder = os.path.basename(env.config['siteFolder'])
        run_drush('site-install minimal  --sites-subdir='+sites_folder+' --site-name="'+settings['name']+'" --account-name=admin --account-pass=admin --db-url=mysql://' + o['user'] + ':' + o['pass'] + '@localhost/'+o['name'])

      if 'deploymentModule' in settings:
        run_drush('en -y '+settings['deploymentModule'])

@task
def copySSHKeyToDocker():
  check_config()
  if not 'dockerKeyFile' in settings:
    print(red('missing dockerKeyFile in fabfile.yaml'))

  key_file = settings['dockerKeyFile']
  run('mkdir -p /root/.ssh')
  put(key_file, '/root/.ssh/id_rsa')
  put(key_file+'.pub', '/root/.ssh/id_rsa.pub')
  run('chmod 600 /root/.ssh/id_rsa')
  run('chmod 644 /root/.ssh/id_rsa.pub')
  run('chmod 700 /root/.ssh')
  put(key_file+'.pub', '/tmp')
  run('cat /tmp/'+os.path.basename(key_file)+'.pub >> /root/.ssh/authorized_keys')
  run('rm /tmp/'+os.path.basename(key_file)+'.pub')
