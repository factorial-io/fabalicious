from os.path import expanduser
from lib import configuration
import logging
log = logging.getLogger('fabric.fabalicious.plugins')

def init(root_folder):
  try:
    __import__('imp').find_module('yapsy')
    from yapsy.PluginManager import PluginManager
    from task import ITaskPlugin

    plugin_dirs = []
    if configuration.getSettings('customTasksFolder'):
      plugin_dirs.append(configuration.fabfile_basedir + '/' + configuration.getSettings('customTasksFolder'))
    plugin_dirs.append(expanduser("~") + '/.fabalicious/plugins/tasks')
    plugin_dirs.append(root_folder + '/plugins/tasks')
    print plugin_dirs

    manager = PluginManager()
    manager.setPluginPlaces(plugin_dirs)
    manager.setCategoriesFilter({
       "Task" : ITaskPlugin,
       })
    manager.collectPlugins()

# Activate all loaded plugins
    for pluginInfo in manager.getAllPlugins():
      manager.activatePluginByName(pluginInfo.name)

    for plugin in manager.getAllPlugins():
      print plugin.plugin_object
      print plugin.name

      if plugin.plugin_object.aliases:
        for alias in plugin.plugin_object.aliases:
          exec("%s=plugin.plugin_object" % (alias))
      else:
        print plugin
        exec("%s=plugin.plugin_object" % (plugin.name))
  except ImportError:
    log.warning('Custom plugins disabled, as yapsi is not installed!')
