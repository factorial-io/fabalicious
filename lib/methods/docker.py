from base import BaseMethod
from fabric.api import *
from fabric.network import *
from fabric.context_managers import settings as _settings
from fabric.colors import green, red
from lib import configuration

class DockerMethod(BaseMethod):

  @staticmethod
  def supports(methodName):
    return methodName == 'docker'


  def getDockerConfig(self, config):
    if not 'docker' in config or 'configuration' not in config['docker']:
      return False

    docker_config_name = config['docker']['configuration']

    dockerHosts = configuration.getSettings('dockerHosts')

    if not dockerHosts or docker_config_name not in dockerHosts:
      return False

    return dockerHosts[docker_config_name]

  def getIp(self, docker_name, docker_host, docker_user, docker_port):
    host_string = join_host_strings(docker_user, docker_host, docker_port)
    print host_string
    try:
      with hide('running', 'output'), _settings( host_string=host_string ):
        output = run('docker inspect --format "{{ .NetworkSettings.IPAddress }}" %s ' % (docker_name))

    except SystemExit:
      print red('Docker not running, can\'t get ip')
      return

    ip_address = output.stdout.strip()
    return ip_address


  def startRemoteAccess(self, config, **kwargs):
    docker_config = self.getDockerConfig(config)
    if not docker_config:
      print red('No docker configuration found!')
      exit(1)

    ip = self.getIp(config['docker']['name'], docker_config['host'], docker_config['user'], docker_config['port'])

    if not ip:
      print red('Could not get docker-ip-address.')
      exit(1)

    public_ip = '0.0.0.0'
    if 'ip' in kwargs:
      public_ip = kwargs['ip']
    print green("I am about to start the port forwarding via SSH. If you are finished, just type exit after the prompt.")
    local("ssh -L%s:8888:%s:80 -p %s %s@%s" % (public_ip, ip, docker_config['port'], docker_config['user'], docker_config['host']))
    exit(0)



  def copySSHKeys(self, config, **kwargs):
    key_file = configuration.getSettings('dockerKeyFile')
    authorized_keys_file = configuration.getSettings('dockerAuthorizedKeyFile')

    with cd(config['rootFolder']), hide('commands', 'output'), lcd(configuration.getBaseDir()):
      run('mkdir -p /root/.ssh')
      if key_file:
        put(key_file, '/root/.ssh/id_rsa')
        put(key_file+'.pub', '/root/.ssh/id_rsa.pub')
        run('chmod 600 /root/.ssh/id_rsa')
        run('chmod 644 /root/.ssh/id_rsa.pub')
        put(key_file+'.pub', '/tmp')
        run('cat /tmp/'+os.path.basename(key_file)+'.pub >> /root/.ssh/authorized_keys')
        run('rm /tmp/'+os.path.basename(key_file)+'.pub')
        print green('Copied keyfile to docker.')

      if authorized_keys_file:
        authorized_keys_file = settings['dockerAuthorizedKeyFile']
        put(authorized_keys_file, '/root/.ssh/authorized_keys')
        print green('Copied authorized keys to docker.')
      run('chmod 700 /root/.ssh')


  def runCommand(self, config, **kwargs):
    command = kwargs['command']
    if not command:
      print red('Missing command for docker-task.')
      exit(1)


    if hasattr(self, command):
      fn = getattr(self, command)
      fn(config, **kwargs)
      return

    docker_config = self.getDockerConfig(config)
    if not docker_config:
      print red('Missing docker-configuration in "%s"' % config.config_name)
      exit(1)

    if command not in docker_config['tasks']:
      print red('Can\'t find subtask "%s" in "%s"' % ( command, ', '.join(docker_config['tasks'].keys())))

    script = docker_config['tasks'][command]

    script_fn = self.factory.get('script', 'runScript')
    variables = { 'dockerHost': docker_config }
    environment = docker_config['environment'] if 'environment' in docker_config else {}
    host_str = docker_config['user'] + '@'+docker_config['host']+':'+str(docker_config['port'])

    execute(script_fn, config, script=script, variables=variables, environment=environment, host=host_str)
