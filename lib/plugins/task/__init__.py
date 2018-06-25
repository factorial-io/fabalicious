from yapsy.IPlugin import IPlugin
from fabric.tasks import Task

class ITaskPlugin(Task, IPlugin):
  def run(self):
    raise NotImplementedError
