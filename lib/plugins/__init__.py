from os.path import expanduser
from lib import configuration
import logging
log = logging.getLogger('fabric.fabalicious.plugins')

def loadPlugins(root_folder, plugin_name, categories_filter):
  from yapsy.PluginManager import PluginManager

  plugin_dirs = []
  plugin_dirs.append(configuration.fabfile_basedir + '/.fabalicious/plugins')
  plugin_dirs.append(expanduser("~") + '/.fabalicious/plugins')
  plugin_dirs.append(root_folder + '/plugins')

  log.debug("Looking for %s-plugins in %s" % (plugin_name, ", ".join(plugin_dirs)))

  manager = PluginManager()
  manager.setPluginPlaces(plugin_dirs)
  manager.setCategoriesFilter(categories_filter)
  manager.collectPlugins()

  # Activate all loaded plugins
  for pluginInfo in manager.getAllPlugins():
    manager.activatePluginByName(pluginInfo.name)

  result = {}
  for plugin in manager.getAllPlugins():

    if hasattr(plugin.plugin_object, 'aliases') and isinstance(plugin.plugin_object.aliases, list):
      for alias in plugin.plugin_object.aliases:
        result[alias] = plugin.plugin_object
    elif hasattr(plugin.plugin_object, 'alias'):
      result[plugin.plugin_object.alias] = plugin.plugin_object
    else:
      result[plugin.name] = plugin.plugin_object
  return result


def getTasks(root_folder):
  try:
    __import__('imp').find_module('yapsy')
    from task import ITaskPlugin

    return loadPlugins(root_folder, 'task', { "Task": ITaskPlugin })

  except ImportError:
    log.warning('Custom plugins disabled, as yapsy is not installed!')
    return {}


def getMethods(root_folder):
  try:
    __import__('imp').find_module('yapsy')
    from method import IMethodPlugin

    return loadPlugins(root_folder, 'method', { "Method": IMethodPlugin })

  except ImportError:
    log.warning('Custom plugins disabled, as yapsy is not installed!')
    return {}
