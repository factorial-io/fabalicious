from fabric.api import *
from fabric.state import output, env
from fabric.colors import green, red


class BaseMethod(object):

  verbose_output = True

  @staticmethod
  def supports(methodName):
    return False

  def __init__(self, methodName, factory):
    self.methodName = methodName
    self.factory = factory


  def preflight(self, task, config, **kwargs):
    pass

  def postflight(self, task, config, **kwargs):
    pass

  def list_remote_files(self, base_folder, patterns):
    result = []
    with cd(base_folder), hide('running', 'output', 'warnings'), warn_only():
      for pattern in patterns:
        cmd = 'ls -l ' + pattern + ' 2>/dev/null'
        output = run(cmd)
        lines = output.stdout.splitlines()
        for line in lines:
          tokens = line.split()

          if(len(tokens) >= 9):
            result.append(tokens[8])
    return result




  def run_quietly(self, cmd, msg = '', hide_output = None, may_fail=False):
    if 'warn_only' in env and env['warn_only']:
      may_fail = True

    if msg != '':
      print msg

    if not hide_output:
      hide_output = ['running', 'output', 'warnings']

    if self.verbose_output:
      hide_output=[]


    with hide(*hide_output):
      try:
        result = run(cmd)

        if not may_fail and result.return_code != 0:
          print red('%s failed:' %s)
          print result

        return result
      except:
        print red('%s failed' % cmd)

        if output['aborts']:
          raise SystemExit('%s failed' % cmd);
