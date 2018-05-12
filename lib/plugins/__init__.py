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
    log.debug("Looking for task-plugins in %s" % ", ".join(plugin_dirs))

    manager = PluginManager()
    manager.setPluginPlaces(plugin_dirs)
    manager.setCategoriesFilter({
       "Task" : ITaskPlugin,
       })
    manager.collectPlugins()

# Activate all loaded plugins
    for pluginInfo in manager.getAllPlugins():
      manager.activatePluginByName(pluginInfo.name)

    result = {}
    for plugin in manager.getAllPlugins():

      if plugin.plugin_object.aliases:
        for alias in plugin.plugin_object.aliases:
          result[alias] = plugin.plugin_object
      else:
        result[plugin.name] = plugin.plugin_object
    return result
  except ImportError:
    log.warning('Custom plugins disabled, as yapsi is not installed!')
    return {}
