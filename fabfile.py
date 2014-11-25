#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import green, red
import datetime
import yaml
import subprocess, shlex, atexit, time
import os.path
import re

settings = 0
current_config = 'unknown'

env.forward_agent = True
env.use_shell = False

class SSHTunnel:
  def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=15):
    self.local_port = local_port

    if not strictHostKeyChecking:
      cmd = 'ssh -o StrictHostKeyChecking=no'
    else:
      cmd = 'ssh'

    cmd = cmd + ' -vAN -L %d:%s:%d %s@%s' % (local_port, dest_host, dest_port, bridge_user, bridge_host)

    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    atexit.register(self.p.kill)
    while not 'Entering interactive session' in self.p.stderr.readline():
      if time.time() > start_time + timeout:
        raise "SSH tunnel timed out"
  def entrance(self):
    return 'localhost:%d' % self.local_port


class RemoteSSHTunnel:
  def __init__(self, config, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=15):
    self.local_port = local_port
    self.bridge_host = bridge_host
    self.bridge_user = bridge_user
    if not strictHostKeyChecking:
      remote_cmd = 'ssh -o StrictHostKeyChecking=no'
      cmd = 'ssh -o StrictHostKeyChecking=no'
    else:
      remote_cmd = 'ssh'
      cmd = 'ssh'
    remote_cmd = remote_cmd + ' -v -L %d:%s:%d %s@%s -A -N -M ' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
    run('rm -f ~/.ssh-tunnel-from-fabric')

    ssh_port = 22
    if 'port' in config:
      ssh_port = config['port']

    cmd = cmd + ' -vA -p %d %s@%s' % (ssh_port, config['user'], config['host'])
    cmd = cmd + " '" + remote_cmd + "'"

    print("running remote tunnel")
    print(cmd);

    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    start_time = time.time()

    start_time = time.time()
    atexit.register(self.p.kill)
    while not 'Entering interactive session' in self.p.stderr.readline():
      if time.time() > start_time + timeout:
        raise "SSH tunnel timed out"


  def entrance(self):
    return 'localhost:%d' % self.local_port




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


def validate_dict(keys, dict, message):
  validated = True
  for key in keys:
    if key not in dict:
      print(red(message + ' ' + key))
      validated = False

  if not validated:
    exit()

def data_merge(dictionary1, dictionary2):
  output = {}
  for item, value in dictionary1.iteritems():
    if dictionary2.has_key(item):
      if isinstance(dictionary2[item], dict):
        output[item] = data_merge(value, dictionary2.pop(item))
    else:
      output[item] = value
  for item, value in dictionary2.iteritems():
    output[item] = value
  return output


def resolve_inheritance(config, all_configs):
  if 'inheritsFrom' in config and config['inheritsFrom'] in all_configs:
    key = config['inheritsFrom']
    base_configuration = resolve_inheritance(all_configs[key], all_configs)
    config = data_merge(base_configuration, config)

  return config

def get_configuration(name):
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

    if not "gitOptions" in settings:
      settings['gitOptions'] = { 'pull' : [ '--no-edit', '--rebase'] }



    host_config = config['hosts'][name]
    host_config = resolve_inheritance(host_config, config['hosts'])

    keys = ("host", "rootFolder", "filesFolder", "siteFolder", "backupFolder", "branch")
    validate_dict(keys, host_config, 'Configuraton '+name+' has missing key')

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

    if "gitOptions" not in host_config:
      host_config['gitOptions'] = settings['gitOptions']

    host_config['gitOptions'] = data_merge(settings['gitOptions'], host_config['gitOptions'])

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


def create_ssh_tunnel(config, tunnel_config, remote=False):
  o = tunnel_config

  if 'destHostFromDockerContainer' in o:
    cmd = 'ssh -p %d %s@%s docker inspect %s | grep IPAddress' % (o['bridgePort'], o['bridgeUser'], o['bridgeHost'], o['destHostFromDockerContainer'])

    try:
      with hide('output'):
        output = local(cmd, capture=True)
    except SystemExit:
      print red('Docker not running, can\'t establish tunnel')
      return

    ip_address = find_between(output.stdout, '"IPAddress": "', '"')
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

  env.use_shell = settings['useShell']
  env.always_use_pty = settings['usePty']

  if 'sshTunnel' in config:
    create_ssh_tunnel(config, config['sshTunnel'])




def check_config():
  if 'config' in env:
    return True

  print(red('no config set! Please use fab config:<your-config> <task>'))
  exit()


def run_custom(config, run_key):

  replacements = {}
  for key in config:
    if type(config[key]) != type({}):
      replacements['%'+key+'%'] = str(config[key])

  pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))

  env.output_prefix = False
  if run_key in config:
    with cd(config['rootFolder']):
      for line in config[run_key]:
        line = pattern.sub(lambda x: replacements[x.group()], line)
        run(line)

  env.output_prefix = True



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
      output = output.stdout.splitlines()
      return output[-1].replace('/', '-')


def get_backup_file_name(config, config_name):
  i = datetime.datetime.now()
  return config['backupFolder'] + "/" +get_version()+ '--' + config_name + "--"+i.strftime('%Y-%m-%d--%H-%M-%S')


def run_common_commands():
  env.output_prefix = False

  key = 'development' if env.config['useForDevelopment'] else 'deployment'
  if key in settings['common']:
    for line in settings['common'][key]:
      run(line)

  env.output_prefix = True


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
          with warn_only():
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
          run('rm -f '+backup_file_name)
          run('rm -f '+backup_file_name+'.gz')
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
def backupDB():
  backup(False)


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

    git_options = ''
    if 'pull' in env.config['gitOptions']:
      git_options = ' '.join(env.config['gitOptions']['pull'])

    run('git pull '+ git_options + ' origin ' +branch)

    if not env.config['ignoreSubmodules']:
      run('git submodule init')
      run('git submodule sync')
      run('git submodule update --init --recursive')

  run_custom(env.config, 'deploy')

  if resetAfterwards and resetAfterwards != '0':
    reset()





@task
def version():
  print green(settings['name'] + ' @ ' + current_config+' tagged with: ' + get_version())


def rsync(config_name, files_type = 'filesFolder'):

  source_config = check_source_config(config_name)

  if not env.config['supportsCopyFrom']:
    print red("The configuration '"+ current_config + "' does not support copyFrom")
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
    rsync += ' -e "ssh -o StrictHostKeyChecking=no -p '+str(source_ssh_port)+'"'
    rsync += ' ' + exclude_files_str
    rsync += ' ' + source_config['user']+'@'+source_config['host']
    rsync += ':' + source_config[files_type]+'/*'
    rsync += ' '
    rsync += env.config[files_type]

    with warn_only():
      run(rsync)


def _copyFilesFrom(config_name = False):
  rsync(config_name)
  source_config = check_source_config(config_name)
  if 'privateFilesFolder' in env.config and 'privateFilesFolder' in source_config:
    rsync(source_config, 'privateFilesFolder')



def _copyDBFrom(config_name = False):
  source_config = check_source_config(config_name)
  target_config = check_source_config(current_config)

  if not env.config['supportsCopyFrom']:
    print red("The configuration '"+ current_config + "' does not support copyFrom")
    return

  print green('Copying database from '+ config_name + " to " + current_config)

  if(env.config['hasDrush']):

    source_ssh_port = '22'
    if 'port' in source_config:
      source_ssh_port = source_config['port']

    ssh_args = ' ' + source_config['user']+'@'+source_config['host']

    no_strict_host_key_checking = False
    if settings['usePty'] == False:
      no_strict_host_key_checking = True

    if 'sshTunnel' in source_config:
      if ('strictHostKeyChecking' in source_config['sshTunnel']) and (source_config['sshTunnel']['strictHostKeyChecking'] == False):
        no_strict_host_key_checking = True

    if no_strict_host_key_checking:
      ssh_args = " -o StrictHostKeyChecking=no" + ssh_args

    sql_name_source = source_config['tmpFolder'] + config_name + '.sql'
    sql_name_target = target_config['tmpFolder'] + config_name + '.sql'

    # drush has no predictable behaviour
    if source_config['supportsZippedBackups']:
      sql_name_target += '.gz'

    # create sql-dump on source
    execute(backup_sql, sql_name_source, source_config, host=source_config['user']+'@'+source_config['host']+':'+str(source_ssh_port))

    if source_config['supportsZippedBackups']:
      sql_name_source += '.gz'


    # copy sql to target
    run('scp -P '+str(source_ssh_port)+' '+ssh_args+':'+sql_name_source+' '+sql_name_target+ ' >>/dev/null')

    # cleanup and remove file from source
    run('ssh -p '+str(source_ssh_port)+' '+ssh_args+' rm ' + sql_name_source)

    # import sql into target
    with cd(env.config['siteFolder']):
      if source_config['supportsZippedBackups']:
        run_drush('zcat '+ sql_name_target + ' | $(drush sql-connect)', False)
      else:
        run_drush('drush sql-cli < ' + sql_name_target, False)

      run('rm '+sql_name_target)


@task
def copyFrom(config_name = False, copyFiles = True, copyDB = True):
  source_config = check_source_config(config_name)
  remote_tunnel = False
  if 'sshTunnel' in source_config:
    remote_tunnel = create_ssh_tunnel(env.config, source_config['sshTunnel'], True)
    tunnel = create_ssh_tunnel(env.config, source_config['sshTunnel'], False)


  if copyFiles:
    _copyFilesFrom(config_name)
  if copyDB:
    _copyDBFrom(config_name)

  if copyDB:
    reset(withPasswordReset=True)


@task
def copyFilesFrom(config_name = False):
  copyFrom(config_name, True, False)


@task
def copyDBFrom(config_name = False):
  copyFrom(config_name, False, True)

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
      mysql_cmd += 'GRANT ALL PRIVILEGES ON '+o['name']+'.* TO '+o['user']+'@localhost IDENTIFIED BY \''+o['pass']+'\'; FLUSH PRIVILEGES;'

      run('mysql -u '+o['user']+' --password='+o['pass']+' -e "'+mysql_cmd+'"')
      with warn_only():
        run('chmod u+w '+env.config['siteFolder'])
        run('chmod u+w '+env.config['siteFolder']+'/settings.php')
        run('rm -f '+env.config['siteFolder']+'/settings.php.old')
        run('mv '+env.config['siteFolder']+'/settings.php '+env.config['siteFolder']+'/settings.php.old 2>/dev/null')

      sites_folder = os.path.basename(env.config['siteFolder'])
      run_drush('site-install minimal  --sites-subdir='+sites_folder+' --site-name="'+settings['name']+'" --account-name=admin --account-pass=admin --db-url=mysql://' + o['user'] + ':' + o['pass'] + '@localhost/'+o['name'])

      if 'deploymentModule' in settings:
        run_drush('en -y '+settings['deploymentModule'])

      reset()
  else:
    print red('Aborting; missing hasDrush, useForDevelopment or supportsInstalls in  '+current_config)

@task
def copySSHKeyToDocker():
  check_config()
  if not 'dockerKeyFile' in settings:
    print(red('missing dockerKeyFile in fabfile.yaml'))

  key_file = settings['dockerKeyFile']

  run('mkdir -p /root/.ssh')
  put(key_file, '/root/.ssh/id_rsa')
  put(key_file+'.pub', '/root/.ssh/id_rsa.pub')
  if 'dockerAuthorizedKeyFile' in settings:
    authorized_keys_file = settings['dockerAuthorizedKeyFile']
    put(authorized_keys_file, '/root/.ssh/authorized_keys')
  run('chmod 600 /root/.ssh/id_rsa')
  run('chmod 644 /root/.ssh/id_rsa.pub')
  run('chmod 700 /root/.ssh')
  put(key_file+'.pub', '/tmp')
  run('cat /tmp/'+os.path.basename(key_file)+'.pub >> /root/.ssh/authorized_keys')
  run('rm /tmp/'+os.path.basename(key_file)+'.pub')



@task
def behat(options='', name=False, format="pretty", out=False):
  check_config()
  if name:
    options += ' --name="' + name + '"'
  if out:
    options += ' --out="' + out + '"'
  options += ' --format="' + format + '"'

  if not 'behatPath' in env.config:
    print(red('missing behatPath in fabfile.yaml'))
    exit()
  env.output_prefix = False
  with cd(env.config['gitRootFolder']):
    run(env.config['behatPath'] + ' ' + options)
  env.output_prefix = True




def expand_subtasks(tasks, task_name):
  commands = []

  for line in tasks[task_name]:
    result = re.match(r'run_task\((.*)\)', line)
    if result:
      sub_task_name = result.group(1)
      if sub_task_name in tasks:
        for cmd in expand_subtasks(tasks, sub_task_name):
          commands.append(cmd)
      else:
        print red("subtask not found in tasks: "+sub_task_name)
        exit()
    else:
      commands.append(line)

  return commands

@task
def docker(subtask='info'):
  check_config()
  if not 'docker' in env.config:
    print red('no docker configuration found.')
    exit()

  # validate host-configuration
  keys = ("name", "configuration")
  validate_dict(keys, env.config['docker'], 'Docker-configuraton '+current_config+' has missing key')


  if not 'dockerHosts' in settings:
    print(red('No dockerHosts-configuration found'))
    exit()

  all_docker_hosts = settings['dockerHosts']
  config_name = env.config['docker']['configuration']
  if not config_name in all_docker_hosts:
    print(red('Could not find docker-configuration %s in dockerHosts' % (config_name)))
    exit()

  docker_configuration = all_docker_hosts[config_name]

  docker_configuration = resolve_inheritance(docker_configuration, all_docker_hosts)

  keys = ("host", "port", "user", "tasks", "rootFolder")
  validate_dict(keys, docker_configuration, 'dockerHosts-Configuraton '+config_name+' has missing key')

  if subtask not in docker_configuration['tasks']:
    print(red('Could not find subtask %s in dockerHosts-configuration %s' % (subtask, config_name)))
    exit()

  print(green("Running task '{subtask}' on guest-host '{docker_host}' for container '{container}'".format(subtask=subtask, docker_host=config_name, container=env.config['docker']['name']) ))

  commands = expand_subtasks(docker_configuration['tasks'], subtask)

  parsed_commands = []

  replacements = {}
  for key in ('user', 'host', 'port', 'branch', 'rootFolder'):
    replacements['%guest.'+key+'%'] = str(env.config[key])
  for key in ('user', 'host', 'port', 'rootFolder'):
    replacements['%'+key+'%'] = str(docker_configuration[key])

  for key in env.config['docker']:
    replacements['%'+key+'%'] = str(env.config['docker'][key])

  pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))

  for line in commands:
    result = pattern.sub(lambda x: replacements[x.group()], line)
    parsed_commands.append(result)

  host_str = docker_configuration['user'] + '@'+docker_configuration['host']+':'+str(docker_configuration['port'])

  if 'password' in docker_configuration:
    env.passwords[host_str]= docker_configuration['password']

  execute(run_script, docker_configuration['rootFolder'], parsed_commands, host=host_str)

@task
def run_script(rootFolder, commands):

  with cd(rootFolder), warn_only():
    for line in commands:
      run(line)


def get_backups_list():
  result = []
  with cd(env.config['backupFolder']), hide('output'), warn_only():
    for ext in ('*.gz', '*.tgz', '*.sql'):
      output = run('ls -l ' + ext + ' 2>/dev/null')
      lines = output.stdout.splitlines()
      for line in lines:
        tokens = line.split()

        if(len(tokens) >= 9):
          line = tokens[8]
          filename, file_ext = os.path.splitext(line)
          if(file_ext == '.gz'):
            filename, file_ext = os.path.splitext(filename)
          tokens = filename.split('--')
          if file_ext == '.sql':
            type = 'sql'
          else:
            type = 'files'
          if(len(tokens) >= 4) and (tokens[1] == current_config):
            result.append({ 'commit': tokens[0], 'date': tokens[2], 'time': tokens[3], 'file': line, 'type': type})

  result = sorted(result, key=lambda k: k['file'], reverse=True)

  return result

@task
def listBackups():
  check_config()
  results = get_backups_list()

  print "\nFound backups for "+ current_config + ":"
  for result in results:

    print "{date} {time}  |  {commit:<30}  |  {file}".format(**result)


@task
def restore(commit, drop=0):
  check_config()

  results = get_backups_list()
  files = { 'sql': False, 'files': False, 'commit': False }
  found = False

  for result in results:
    if result['commit'] == commit:
      files[result['type']] = result['file']
      files['commit'] = result['commit']
      found = True

  if not found:
    print 'Could not find requested commit, trying by file-name ...'
    for result in results:
      if result['file'].find(commit) >= 0:
        files[result['type']] = result['file']
        files['commit'] = result['commit']
        found = True

  if not found:
    print red('Could not find requested backup ' + commit+'!')
    list_backups();
    exit()

  # restore sql
  if files['sql']:
    with cd(env.config['siteFolder']):

      if drop:
        run_drush('sql-drop')

      sql_name_target = env.config['backupFolder'] + '/' + files['sql']
      if env.config['supportsZippedBackups']:
        run_drush('zcat '+ sql_name_target + ' | $(drush sql-connect)', False)
      else:
        run_drush('drush sql-cli < ' + sql_name_target, False)

      print(green('SQL restored from ' + files['sql']))


  # restore files
  if files['files']:
    # move current files folder to backup
    ts = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
    old_files_folder = env.config['filesFolder'] + '.' + ts + '.old'
    with warn_only():
      run('chmod -R u+x '+env.config['filesFolder'])
      run('rm -rf '+ old_files_folder)
      run('mv ' + env.config['filesFolder'] + ' '+old_files_folder)

    tar_file = env.config['backupFolder'] + '/' + files['files']
    run('mkdir -p ' + env.config['filesFolder'])
    with cd(env.config['filesFolder']):
      run('tar -xzvf ' + tar_file)

    print(green('files restored from ' + files['files']))

  # restore git
  with cd(env.config['gitRootFolder']):

    run('git checkout ' + result['commit'])

    print(green('source restored to ' + files['commit']))

  reset()


@task
def updateDrupalCore(version=7):
  check_config()
  if not env.config['useForDevelopment']:
    print red('drupalUpdate not supported for staging/live environments ...')
    exit

  backupDB()

  # create new branch
  with cd(env.config['gitRootFolder']):
    run('git checkout -b "drupal-update"')

  # download drupal
  with cd(env.config['rootFolder']):
    run('rm -rf /tmp/drupal-update')
    run('mkdir -p /tmp/drupal-update')
    run_drush('dl --destination="/tmp/drupal-update" --default-major="%d" drupal ' % version)

  # copy files to root-folder
  with(cd('/tmp/drupal-update')):
    drupal_folder = run('ls').stdout.strip()
    print drupal_folder

    run('rsync -rav --no-o --no-g %s/* %s' % (drupal_folder, env.config['rootFolder']) )

  # remove temporary files
  with cd(env.config['rootFolder']):
    run('rm -rf /tmp/drupal-update')

  print green("Updated drupal successfully to '%s'. Please review the changes in the new branch drupal-update." % drupal_folder)

