from fabric.api import *
import subprocess, shlex, atexit, time
import time
from fabric.colors import red

ssh_no_strict_key_host_checking_params = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '

class TunnelBase:

  def waitForInteractiveSessions(self, timeout, waitForSendingCommand):
    start_time = time.time()
    connectionEstablished = False
    commandSent = not waitForSendingCommand
    terminated = False
    output = ''
    while not connectionEstablished and not terminated:
      line = self.p.stderr.readline()
      output += line

      self.p.poll()
      if self.p.returncode != None:
        terminated = True

      if "Sending command" in line:
        commandSent = True

      if commandSent and 'Entering interactive session' in line:
        connectionEstablished = True

      if time.time() > start_time + timeout:
        terminated = True

    if not connectionEstablished:
      print red("Could not establish tunnel with command %s" % self.cmd)
      print output
      exit(1)

  def terminate(self):
    if self.p.returncode == None:
      self.p.kill()


class SSHTunnel(TunnelBase):

  @staticmethod
  def getSSHCommand(bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True):
    args = {
        "local_port": local_port,
        "dest_host": dest_host,
        "dest_port": dest_port,
        "bridge_user": bridge_user,
        "bridge_host": bridge_host,
        "bridge_port": bridge_port
    }

    if not strictHostKeyChecking:
      cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
    else:
      cmd = 'ssh'

    cmd = cmd + ' -q -o PasswordAuthentication=no -vAN -L {local_port}:{dest_host}:{dest_port} -p {bridge_port} {bridge_user}@{bridge_host}'.format(**args)
    return cmd

  def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=45):
    self.local_port = local_port

    self.cmd = cmd = self.getSSHCommand(bridge_user, bridge_host, dest_host, bridge_port, dest_port, local_port, strictHostKeyChecking)

    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    atexit.register(self.terminate)
    self.waitForInteractiveSessions(timeout, False)

  def entrance(self):
    return 'localhost:%d' % self.local_port



class RemoteSSHTunnel(TunnelBase):

  @staticmethod
  def getSSHCommand(config, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True):
    args = {
        "local_port": local_port,
        "dest_host": dest_host,
        "dest_port": dest_port,
        "bridge_user": bridge_user,
        "bridge_host": bridge_host,
        "bridge_port": bridge_port,
        "ssh_user": config['user'],
        'ssh_host': config['host'],
        'ssh_port': config['port'] if 'port' in config else 22
    }
    if not strictHostKeyChecking:
      remote_cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
      cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
    else:
      remote_cmd = 'ssh'
      cmd = 'ssh'
    remote_cmd = remote_cmd + ' -q -o PasswordAuthentication=no -v -L {local_port}:{dest_host}:{dest_port} -p {bridge_port} {bridge_user}@{bridge_host} -A -N -M '

    with hide('running', 'output', 'warnings'):
      run('rm -f ~/.ssh-tunnel-from-fabric')

    ssh_port = 22
    if 'port' in config:
      ssh_port = config['port']

    cmd = cmd + ' -o PasswordAuthentication=no -vA -p {ssh_port} {ssh_user}@{ssh_host}'
    cmd = cmd + " '" + remote_cmd + "'"
    cmd = cmd.format(**args)

    return cmd


  def __init__(self, config, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=90):
    self.local_port = local_port
    self.bridge_host = bridge_host
    self.bridge_user = bridge_user

    self.cmd = cmd = self.getSSHCommand(config, bridge_user, bridge_host, dest_host, bridge_port, dest_port, local_port, strictHostKeyChecking)

    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    atexit.register(self.terminate)
    self.waitForInteractiveSessions(timeout, True)

    time.sleep(5)

  def entrance(self):
    return 'localhost:%d' % self.local_port


def validate_dict(keys, dict, section=False):
  result = {}
  for key in keys:
    if key not in dict:
      if section:
        result[key] = 'Key is missing in section \'%s\'' % section
      else:
        result[key] = 'Key is missing'

  return result

