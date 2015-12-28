from base import BaseMethod
from fabric.api import *
from lib.utils import SSHTunnel, RemoteSSHTunnel
from fabric.colors import green, red

class SSHMethod(BaseMethod):
  tunnel_creating = False
  tunnel_created = False
  tunnel = None
  remote_tunnel = None

  @staticmethod
  def supports(methodName):
    return methodName == 'ssh'

  def create_ssh_tunnel(self, config, tunnel_config, remote=False):
    o = tunnel_config

    if 'destHost' not in o:
      print "get remote ip-address from available methods ...",
      # check other methods for gathering the desthost-ip-address.
      result = {}
      self.factory.runTask(config, 'getIpAddress', result=result)
      if 'ip' in result:
        o['destHost'] = result['ip']

    if 'destHost' not in o:
      print red('Could not get remote ip-address from existing method, tunnel creation failed.')
      return False


    #if 'destHostFromDockerContainer' in o:

      #ip_address = get_docker_container_ip(o['destHostFromDockerContainer'], o['bridgeHost'], o['bridgeUser'], o['bridgePort'])

      #if not ip_address:
        #print red('Docker not running, can\'t establish tunnel')
        #return

      #print(green("Docker container " + o['destHostFromDockerContainer'] + " uses IP " + ip_address))

      #o['destHost'] = ip_address

    strictHostKeyChecking = o['strictHostKeyChecking'] if 'strictHostKeyChecking' in o else True

    if remote:
      tunnel = RemoteSSHTunnel(config, o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)
    else:
      tunnel = SSHTunnel(o['bridgeUser'], o['bridgeHost'], o['destHost'], o['bridgePort'], o['destPort'], o['localPort'], strictHostKeyChecking)

    return tunnel


  def preflight(self, task, config, **kwargs):
    if 'sshTunnel' in config and not self.tunnel_created:
      if not self.tunnel_creating:
        self.tunnel_creating = True
        print "Establishing SSH-Tunnel...",

        self.tunnel = self.create_ssh_tunnel(config, config['sshTunnel'], False)

        self.tunnel_created = self.tunnel != False
        if self.tunnel_created:
          print green('Tunnel is established')
        self.tunnel_creating = False





