from fabric.api import *
from fabric.state import output, env


class BaseMethod(object):

  verbose_output = True

  @staticmethod
  def supports(methodName):
    return False

  def __init__(self, methodName):
    self.methodName = methodName


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
