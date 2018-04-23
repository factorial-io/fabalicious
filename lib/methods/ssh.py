from base import BaseMethod
from fabric.api import *
from lib.utils import SSHTunnel, RemoteSSHTunnel
from fabric.colors import green, red
from fabric.network import *
from lib import configuration
import copy
import random
from lib.utils import validate_dict

class SSHMethod(BaseMethod):
  tunnels = {}
  tunnelCreating = False
  sshPorts = {}


  @staticmethod
  def supports(methodName):
    return methodName == 'ssh'

  @staticmethod
  def validateConfig(config):
    keys = ['host', 'user'];
    return validate_dict(keys, config)

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    defaults['usePty'] = settings['usePty']
    defaults['useShell'] = settings['useShell']
    defaults['disableKnownHosts'] = settings['disableKnownHosts']

  @staticmethod
  def applyConfig(config, settings):
    if 'sshTunnel' in config and not isinstance(config['sshTunnel'], dict):
      del(config['sshTunnel'])

    if "sshTunnel" in config and  "docker" in config:
      docker_name = config["docker"]["name"]
      config["sshTunnel"]["destHostFromDockerContainer"] = docker_name

    if "sshTunnel" in config:
      if not 'localPort' in config['sshTunnel']:
        if 'port' in config:
          config['sshTunnel']['localPort'] = config['port']
        else:

          if config['config_name'] not in SSHMethod.sshPorts:
            SSHMethod.sshPorts[config['config_name']] = random.randrange(1025, 65535)

          port = SSHMethod.sshPorts[config['config_name']]
          config['sshTunnel']['localPort'] = port
          config['port'] = port

    if 'port' not in config:
      config['port'] = 22

  def getHostConfig(self, config, hostConfig):
    for key in ['host', 'port', 'user']:
      hostConfig[key] = config[key]



  def openShell (self, config):
    with cd(config['rootFolder']):
      open_shell()

  def printShell (self, config):
    cmd = 'ssh -A -p {port} {user}@{host}'.format(**config)

    if 'sshTunnel' in config:
      cmd = 'ssh -A -J {jump_user}@{jump_host}:{jump_port} -p {port} {user}@{host}'.format(
        jump_host = config['sshTunnel']['bridgeHost'],
        jump_user = config['sshTunnel']['bridgeUser'],
        jump_port = config['sshTunnel']['bridgePort'],
        port = config['sshTunnel']['destPort'],
        user = config['user'],
        host = config['sshTunnel']['destHost']
      )

    return cmd

  def create_ssh_tunnel(self, msg, source_config, target_config, remote=False):

    key = source_config['config_name'] + "--" + target_config['config_name']
    if remote:
      key = key + '--remote'

    if key not in self.tunnels:
      self.tunnels[key] = {'creating': False, 'tunnel': None, 'created': False }

    if self.tunnels[key]['creating'] or self.tunnels[key]['created']:
      return self.tunnels[key]['tunnel']

    self.tunnels[key]['creating'] = True

    print "%s" % msg,

    o = copy.deepcopy(target_config['sshTunnel'])

    if 'destHost' not in o:
      print "get remote ip-address ...",
      # check other methods for gathering the desthost-ip-address.
      result = {}
      self.factory.runTask(target_config, 'getIpAddress', result=result, quiet=True)
      if 'ip' in result:
        o['destHost'] = result['ip']

    if 'destHost' not in o or not o['destHost']:
      print red('Could not get remote ip-address!')
      self.tunnels[key]['creating'] = False

      return False

    strictHostKeyChecking = o['strictHostKeyChecking'] if 'strictHostKeyChecking' in o else True

    if remote:
      tunnel = RemoteSSHTunnel(source_config, o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)
    else:
      tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)

    self.tunnels[key]['tunnel'] = tunnel
    self.tunnels[key]['created'] = tunnel != False
    self.tunnels[key]['creating'] = False

    if self.tunnels[key]['created']:
      print green('Tunnel established')
    else:
      print red('Tunnel creation failed')

    return tunnel


  def createTunnelFromLocalToHost(self, config):
    msg = "Establishing SSH-Tunnel from local to {config_name}...".format(**config),
    self.create_ssh_tunnel(msg, config, config, False)



  def createTunnelFromLocalToSource(self, config, source_config):
    msg = "Establishing SSH-Tunnel from local to source {config_name}...".format(**source_config),
    self.create_ssh_tunnel(msg, config, source_config, False)


  def createTunnelFromHostToSource(self, config, source_config):
    msg = "Establishing SSH-Tunnel from host %s to source %s..." % (config['config_name'], source_config['config_name']),
    self.create_ssh_tunnel(msg, config, source_config, True)


  def preflightImpl(self, task, config, **kwargs):
    # check if current config needs a tunnel
    if task != 'doctor' and task != 'printShell' and 'sshTunnel' in config:
      self.createTunnelFromLocalToHost(config)
    # copyDBFrom and copyFilesFrom may need additional tunnels
    if (task == 'copyDBFrom' or task == 'copyFilesFrom'):
      source_config = kwargs['source_config']
      if source_config and 'sshTunnel' in source_config:
        self.createTunnelFromLocalToSource(config, source_config)
        if not config['runLocally']:
          self.createTunnelFromHostToSource(config, source_config)


  def preflight(self, task, config, **kwargs):
    # print('ssh.preflight: %s %s' % (self.tunnel_creating, config['config_name']))
    if not self.tunnelCreating:
      self.tunnelCreating = True
      self.preflightImpl(task, config, **kwargs)
      self.tunnelCreating = False


  def doctor_ssh_connection(self, config):
    output = local('ssh -A -o StrictHostKeyChecking=no -o PasswordAuthentication=no -o BatchMode=yes -o ConnectTimeout=5 -p {port} {user}@{host} echo ok'.format(**config), capture=True)
    if output.return_code != 0:
      print red('Cannot connect to host! Please check if the host is running and reachable, and check if your public key is added to authorized_keys on the remote host.')
      print red('Try: ssh -p {port} {user}@{host}'.format(**config))
      print red('Try: ssh-copy-id -p {port} {user}@{host}'.format(**config))
      print red('Try: ssh-keyscan -t rsa,dsa -p {port} -H {host} and add the lines to known_hosts if not already in place.'.format(**config))
      return False
    else:
      print green("Can connect to host {host} at port {port}!".format(**config))
      return True


  def doctor(self, config, **kwargs):
    with hide('output', 'running'), warn_only():
      print "Check SSH keyforwading: ",
      output = local(' echo xx${SSH_AUTH_SOCK}xx', capture=True)
      if output.stdout.strip() == 'xxxx':
        print red('SSH Keyforwarding is not working correctly, SSH_AUTH_SOCK is not available!')
        exit(1)
      else:
        print green('SSH Keyforwarding seems to work.')

      print "Check SSH key-agent: ",
      output = local('ssh-add -l', capture=True)
      if output.return_code != 0:
        print red('SSH key-agent has no private keys, please add it via "ssh-add".')
        exit(1)
      else:
        print green('SSH key-agent has one or more private keys.')

      if 'sshTunnel' in config:
        print "Check SSH tunnel: ",
        cfg = config['sshTunnel']
        if not self.doctor_ssh_connection({ 'host': cfg['bridgeHost'], 'port': cfg['bridgePort'], 'user': cfg['bridgeUser']}):
          exit(1)

        self.preflight('dummyTask', config)


      print "Check SSH connection: ",
      if not self.doctor_ssh_connection(config):
        exit(1)

      if 'remote' in kwargs:
        remote_config = configuration.get(kwargs['remote'])

        if 'sshTunnel' in remote_config:
          # First check if we can ssh into bridge-host.
          print "Check SSH tunnel to remote source: ",
          cfg = remote_config['sshTunnel']
          if not self.doctor_ssh_connection({ 'host': cfg['bridgeHost'], 'port': cfg['bridgePort'], 'user': cfg['bridgeUser']}):
            exit(1)

          # create tunnel
          self.createTunnelFromLocalToSource(config, remote_config)

        # ssh from local into remote host
        if not self.doctor_ssh_connection(remote_config):
          exit(1)

        # Test ssh connection from inside host to source host.
        if 'sshTunnel' in remote_config:
          self.createTunnelFromHostToSource(config, remote_config)

        ssh_cmd = 'ssh -A -o StrictHostKeyChecking=no -o PasswordAuthentication=no -o BatchMode=yes -o ConnectTimeout=5'
        cmd_on_host = ssh_cmd + " -p {port} {user}@{host} echo ok".format(**remote_config)
        cmd = ssh_cmd + ' -p {port} {user}@{host} "' + cmd_on_host + '"'

        cmd = cmd.format(**config)
        print "Check SSH-connection from %s to %s: " % (config['config_name'], remote_config['config_name']),
        output = local(cmd, capture=True)
        if output.return_code != 0:
          print red('Connection failed!')
          print red('Try: %s' % cmd)
          print output.stdout
          exit(1)
        else:
          print green('Connection established!')








