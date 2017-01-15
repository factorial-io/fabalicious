from base import BaseMethod
from fabric.api import *
from lib.utils import SSHTunnel, RemoteSSHTunnel
from fabric.colors import green, red
from fabric.network import *
from lib import configuration
import copy
from lib.utils import validate_dict

class SSHMethod(BaseMethod):
  tunnel_creating = False
  tunnel_created = False
  source_tunnel_created = False
  tunnel = None
  source_tunnel = None
  source_remote_tunnel = None
  creatingTunnelFromLocalToHost = False
  creatingTunnelFromHostToSource = False
  creatingTunnelFromLocalToSourceHost = False


  @staticmethod
  def supports(methodName):
    return methodName == 'ssh'

  @staticmethod
  def validateConfig(config):
    keys = ['host', 'port', 'user'];
    return validate_dict(keys, config)

  @staticmethod
  def getDefaultConfig(config, settings, defaults):
    defaults['port'] = 22
    defaults['usePty'] = settings['usePty']
    defaults['useShell'] = settings['useShell']
    defaults['disableKnownHosts'] = settings['disableKnownHosts']

  @staticmethod
  def applyConfig(config, settings):
    if "sshTunnel" in config and "docker" in config:
      docker_name = config["docker"]["name"]
      config["sshTunnel"]["destHostFromDockerContainer"] = docker_name

    if "sshTunnel" in config:
      if not 'localPort' in config['sshTunnel']:
        config['sshTunnel']['localPort'] = config['port']




  def openShell (self, config):
    with cd(config['rootFolder']):
      open_shell()


  def create_ssh_tunnel(self, source_config, target_config, remote=False):
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
      return False

    strictHostKeyChecking = o['strictHostKeyChecking'] if 'strictHostKeyChecking' in o else True

    if remote:
      tunnel = RemoteSSHTunnel(source_config, o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)
    else:
      tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)

    return tunnel


  def createTunnelFromLocalToHost(self, config):
    if self.creatingTunnelFromLocalToHost:
      return
    self.creatingTunnelFromLocalToHost = True

    print "Establishing SSH-Tunnel from local to {config_name}...".format(**config),

    self.tunnel = self.create_ssh_tunnel(config, config, False)

    self.tunnel_created = self.tunnel != False
    if self.tunnel_created:
      print green('Tunnel is established')

    self.creatingTunnelFromLocalToHost = False


  def createTunnelFromLocalToSource(self, config, source_config):
    if self.creatingTunnelFromLocalToSourceHost:
      return
    self.creatingTunnelFromLocalToSourceHost = True

    print "Establishing SSH-Tunnel from local to source {config_name}...".format(**source_config),

    self.source_tunnel = self.create_ssh_tunnel(config, source_config, False)

    self.source_tunnel_created = self.source_tunnel != False
    if self.source_tunnel_created:
      print green('Tunnel is established')

    self.creatingTunnelFromLocalToSourceHost = False


  def createTunnelFromHostToSource(self, config, source_config):
    if self.creatingTunnelFromHostToSource:
      return
    self.creatingTunnelFromHostToSource = True

    print "Establishing SSH-Tunnel from host %s to source %s..." % (config['config_name'], source_config['config_name']),

    self.remote_source_tunnel = self.create_ssh_tunnel(config, source_config, True)

    self.remote_source_tunnel_created = self.remote_source_tunnel != False
    if self.remote_source_tunnel_created:
      print green('Tunnel is established')

    self.creatingTunnelFromHostToSource = False


  def preflightImpl(self, task, config, **kwargs):
    # check if current config needs a tunnel
    if task != 'doctor' and 'sshTunnel' in config and not self.tunnel_created:
      self.createTunnelFromLocalToHost(config)
    # copyDBFrom and copyFilesFrom may need additional tunnels
    if (task == 'copyDBFrom' or task == 'copyFilesFrom'):
      source_config = kwargs['source_config']
      if source_config and 'sshTunnel' in source_config and not self.source_tunnel_created:
        self.createTunnelFromLocalToSource(config, source_config)
        self.createTunnelFromHostToSource(config, source_config)


  def preflight(self, task, config, **kwargs):
    # print('ssh.preflight: %s %s' % (self.tunnel_creating, config['config_name']))
    if not self.tunnel_creating:
      self.tunnel_creating = True
      self.preflightImpl(task, config, **kwargs)
      self.tunnel_creating = False


  def doctor_ssh_connection(self, config):
    output = local('ssh -o "StrictHostKeyChecking no" -o PasswordAuthentication=no -o BatchMode=yes -o ConnectTimeout=5 -p {port} {user}@{host} echo ok'.format(**config), capture=True)
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
          print "Check SSH tunnel to remote source: ",
          cfg = remote_config['sshTunnel']
          if not self.doctor_ssh_connection({ 'host': cfg['bridgeHost'], 'port': cfg['bridgePort'], 'user': cfg['bridgeUser']}):
            exit(1)






