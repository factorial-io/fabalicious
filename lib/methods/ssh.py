from base import BaseMethod
from fabric.api import *
from lib.utils import SSHTunnel, RemoteSSHTunnel
from fabric.colors import green, red
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

  def preflightImpl(self, task, config, **kwargs):
    # check if current config needs a tunnel
    if 'sshTunnel' in config and not self.tunnel_created:
      print "Establishing SSH-Tunnel...",

      self.tunnel = self.create_ssh_tunnel(config, config, False)

      self.tunnel_created = self.tunnel != False
      if self.tunnel_created:
        print green('Tunnel is established')

    # copyDBFrom and copyFilesFrom may need additional tunnels
    if (task == 'copyDBFrom' or task == 'copyFilesFrom'):
      source_config = kwargs['source_config']
      if source_config and 'sshTunnel' in source_config and not self.source_tunnel_created:
        print "Establishing SSH-Tunnel to source ...",
        self.source_tunnel = self.create_ssh_tunnel(config, source_config, False)
        self.source_remote_tunnel = self.create_ssh_tunnel(config, source_config, True)

        self.source_tunnel_created = self.source_tunnel != False and self.source_remote_tunnel != False
        if self.source_tunnel_created:
          print green('Tunnel is established')


  def preflight(self, task, config, **kwargs):
    # print('ssh.preflight: %s %s' % (self.tunnel_creating, config['config_name']))
    if not self.tunnel_creating:
      self.tunnel_creating = True
      self.preflightImpl(task, config, **kwargs)
      self.tunnel_creating = False



