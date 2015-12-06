from base import BaseMethod
from fabric.api import *

class SSHMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'ssh'





