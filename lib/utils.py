from fabric.api import *
import subprocess, shlex, atexit, time


ssh_no_strict_key_host_checking_params = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q'

class SSHTunnel:
  def __init__(self, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=45):
    self.local_port = local_port

    if not strictHostKeyChecking:
      cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
    else:
      cmd = 'ssh'

    cmd = cmd + ' -vAN -L %d:%s:%d %s@%s' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    atexit.register(self.p.kill)
    while not 'Entering interactive session' in self.p.stderr.readline():
      if time.time() > start_time + timeout:
        raise Exception("SSH tunnel timed out")
  def entrance(self):
    return 'localhost:%d' % self.local_port

class RemoteSSHTunnel:
  def __init__(self, config, bridge_user, bridge_host, dest_host, bridge_port=22, dest_port=22, local_port=2022, strictHostKeyChecking = True, timeout=90):
    self.local_port = local_port
    self.bridge_host = bridge_host
    self.bridge_user = bridge_user
    if not strictHostKeyChecking:
      remote_cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
      cmd = 'ssh ' + ssh_no_strict_key_host_checking_params
    else:
      remote_cmd = 'ssh'
      cmd = 'ssh'
    remote_cmd = remote_cmd + ' -v -L %d:%s:%d %s@%s -A -N -M ' % (local_port, dest_host, dest_port, bridge_user, bridge_host)
    with hide('running', 'output', 'warnings'):
      run('rm -f ~/.ssh-tunnel-from-fabric')

    ssh_port = 22
    if 'port' in config:
      ssh_port = config['port']

    cmd = cmd + ' -vA -p %d %s@%s' % (ssh_port, config['user'], config['host'])
    cmd = cmd + " '" + remote_cmd + "'"

    print(cmd),

    self.p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    start_time = time.time()

    start_time = time.time()
    atexit.register(self.p.kill)
    while not 'Entering interactive session' in self.p.stderr.readline():
      if time.time() > start_time + timeout:
        raise Exception('SSH tunnel timed out with command "%s"' % cmd)


  def entrance(self):
    return 'localhost:%d' % self.local_port

