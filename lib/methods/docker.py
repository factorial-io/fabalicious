import logging
log = logging.getLogger('fabalicious.docker')

from base import BaseMethod
from fabric.api import *
from fabric.network import *
from fabric.context_managers import settings as _settings
from fabric.context_managers import env
from lib import configuration
import copy
from lib.utils import validate_dict
import tempfile

class DockerMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'docker'

  @staticmethod
  def validateConfig(config):
    if 'docker' not in config:
      return validate_dict(['docker'], config)

    return validate_dict(['configuration', 'name'], config['docker'], 'docker')

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    pass

  @staticmethod
  def applyConfig(config, settings):
    config_name = config['docker']['configuration']
    data = False
    # Check if configuration points to an external source.
    if config_name[0:7] == 'http://' or config_name[0:8] == 'https://':
      data = configuration.get_configuration_via_http(config_name)
      data = configuration.resolve_inheritance(data, {})
    elif config_name[0:1] == '.':
      data = configuration.get_configuration_via_file(config_name)
      data = configuration.resolve_inheritance(data, {})
    if data:
      settings['dockerHosts'][config_name] = data

    if 'tag' not in config['docker']:
      config['docker']['tag'] = 'latest'

    BaseMethod.addExecutables(config, ['supervisorctl'])

  @staticmethod
  def getInternalCommands():
    return ['copySSHKeys', 'startRemoteAccess', 'waitForServices'];

  def getDockerConfig(self, config):
    if not 'docker' in config or 'configuration' not in config['docker']:
      return False

    docker_config_name = config['docker']['configuration']
    docker_config = configuration.getDockerConfig(docker_config_name, config['runLocally'])

    if docker_config and 'password' in docker_config:
      self.addPasswordToFabricCache(**docker_config)


    return docker_config

  def getHostConfig(self, config, hostConfig):
    dockerConfig = self.getDockerConfig(config)
    for key in ['host', 'port', 'user']:
      hostConfig[key] = dockerConfig[key]

  def getIp(self, docker_name, docker_host, docker_user, docker_port):
    host_string = join_host_strings(docker_user, docker_host, docker_port)
    try:
      with hide('running', 'output', 'warnings'), _settings( host_string=host_string, warn_only=True ):
        output = run('docker inspect --format "{{ .NetworkSettings.IPAddress }}" %s ' % (docker_name))

    except SystemExit:
      log.error('Docker not running, can\'t get ip')
      return False

    ip_address = output.stdout.strip()
    if output.return_code != 0:
      return False

    return ip_address


  def getIpAddress(self, config, **kwargs):
    docker_config = self.getDockerConfig(config)
    if docker_config:
      ip = self.getIp(config['docker']['name'], docker_config['host'], docker_config['user'], docker_config['port'])
      if 'result' in kwargs:
        kwargs['result']['ip'] = ip
      return ip if ip else False

    return False


  def startRemoteAccess(self, config, port="80", publicPort="8888", **kwargs):
    docker_config = self.getDockerConfig(config)
    if not docker_config:
      log.error('No docker configuration found!')
      exit(1)

    ip = self.getIpAddress(config)

    if not ip:
      log.error('Could not get docker-ip-address of docker-container %s.' % config['docker']['name'])
      exit(1)

    public_ip = '0.0.0.0'
    if 'ip' in kwargs:
      public_ip = kwargs['ip']
    log.info("I am about to start the port forwarding via SSH. If you are finished, just type exit after the prompt.")
    local("ssh -L%s:%s:%s:%s -p %s %s@%s" % (public_ip, publicPort, ip, port, docker_config['port'], docker_config['user'], docker_config['host']))
    exit(0)

  def about(self, config, **kwargs):
    data = kwargs['data']
    docker_config = self.getDockerConfig(config)
    if docker_config:
      data['DockerHost-configuration'] = docker_config


  def copySSHKeys(self, config, **kwargs):
    if 'ssh' not in config['needs']:
      return
    tempfiles = []
    files = {
      'key': configuration.getSettings('dockerKeyFile'),
      'authorized_keys': configuration.getSettings('dockerAuthorizedKeyFile'),
      'known_hosts': configuration.getSettings('dockerKnownHostsFile')
    }
    if files['key']:
      files['public_key'] = files['key'] + '.pub'

    # Check existance of source files
    count = 0;
    preflight_succeeded = True
    for key, value in files.iteritems():
      if not value:
        count += 1
      else:
        full_file_name = value

        if value[0:7] == 'http://' or value[0:8] == 'https://':
          data = configuration.get_configuration_via_http(value, as_yaml=False)
          if not data:
            preflight_succeeded = False
            continue;
          else:
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as tmp:
              tmp.write(data)
            tempfiles.append(path)
            full_file_name = path
        else:
          full_file_name = configuration.getBaseDir() + '/' + value

        if not os.path.exists(full_file_name):
          log.error('Could not copy file to container, missing file: %s' % full_file_name)
          preflight_succeeded = False
        else:
          files[key] = full_file_name

    if count >= 3:
      return

    if not preflight_succeeded:
      exit(1)

    with cd(config['rootFolder']), hide('commands', 'output'), lcd(configuration.getBaseDir()):
      run('mkdir -p /root/.ssh')
      if files['key']:
        put(files['key'], '/root/.ssh/id_rsa')
        put(files['public_key'], '/root/.ssh/id_rsa.pub')
        run('chmod 600 /root/.ssh/id_rsa')
        run('chmod 644 /root/.ssh/id_rsa.pub')
        put(files['public_key'], '/tmp')
        run('cat /tmp/'+os.path.basename(files['public_key'])+' >> /root/.ssh/authorized_keys')
        run('rm /tmp/'+os.path.basename(files['public_key']))
        log.info('Copied keyfile to docker.')

      if files['authorized_keys']:
        put(files['authorized_keys'], '/root/.ssh/authorized_keys')
        log.info('Copied authorized keys to docker.')

      if files['known_hosts']:
        put(files['known_hosts'], '/root/.ssh/known_hosts')
        log.info('Copied known hosts to docker.')

      run('chmod 700 /root/.ssh')

    for file in tempfiles:
      os.remove(file)

  def waitForServices(self, config, **kwargs):
    if 'ssh' not in config['needs'] or not config['executables']['supervisorctl']:
      return

    host_string = join_host_strings(config['user'], config['host'], config['port'])
    if 'password' in config:
      self.addPasswordToFabricCache(**config)

    max_tries = 20
    try_n = 0

    while(True):
      try_n += 1
      try:
        with cd(config['rootFolder']), hide('commands'), _settings( host_string=host_string ):

          output = run('supervisorctl status')
          output = output.stdout.splitlines()
          count_running = 0
          count_services = 0;
          for line in output:
            if line.strip() != '':
              count_services += 1
              if line.find('RUNNING'):
                count_running += 1
          if count_services == count_running:
            log.info('Services up and running!')
            break;

      except:
        # TODO:
        # handle only relevant exceptions like
        # fabric.exceptions.NetworkError

        if (try_n < max_tries):
          # Let's wait and try again...
          print "Wait for 5 secs and try again."
          time.sleep(5)
        else:
          log.error("Supervisord not coming up at all")
          break

  def listAvailableCommands(self, config):
    if not config:
      return

    docker_config = self.getDockerConfig(config)
    if not docker_config:
      return

    print "Available docker-commands:"
    internal_commands = self.getInternalCommands()
    available_commands = internal_commands + docker_config['tasks'].keys()
    for command in sorted(available_commands):
      print "- %s" % command


  def runCommand(self, config, **kwargs):
    command = kwargs['command']
    if not command:
      log.error('Missing command for docker-task.')
      self.listAvailableCommands(config)
      exit(1)


    if  command not in ['exists', 'run', 'cd'] and hasattr(self, command):
      fn = getattr(self, command)
      fn(config, **kwargs)
      return

    docker_config = self.getDockerConfig(config)
    if not docker_config:
      log.error('Missing or incorrect docker-configuration in "%s"' % config['config_name'])
      exit(1)

    if command not in docker_config['tasks']:
      log.error('Can\'t find  docker-command "%s"'  % ( command ))
      self.listAvailableCommands(config)
      exit(1)

    script = docker_config['tasks'][command]
    script_fn = self.factory.get('script', 'runScript')
    variables = { 'dockerHost': docker_config }
    environment = docker_config['environment'] if 'environment' in docker_config else {}
    runLocally = docker_config['runLocally'] if 'runLocally' in docker_config else config['runLocally']

    if runLocally:
      execute(script_fn, config, script=script, variables=variables, environment=environment, rootFolder = docker_config['rootFolder'], runLocally=runLocally)
    else:
      host_str = docker_config['user'] + '@'+docker_config['host']+':'+str(docker_config['port'])
      execute(script_fn, config, script=script, variables=variables, environment=environment, host=host_str, runLocally=runLocally, rootFolder = docker_config['rootFolder'])


  def createApp(self, config, stage, dockerConfig, **kwargs):
    if stage in dockerConfig['tasks'] or stage in ['spinUp', 'spinDown', 'deleteContainer']:
      self.runCommand(config, command=stage)


  def destroyApp(self, config, stage, dockerConfig, **kwargs):
    if stage in dockerConfig['tasks'] or stage in ['spinUp', 'spinDown', 'deleteContainer']:
      self.runCommand(config, command=stage)
