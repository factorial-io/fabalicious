from os.path import expanduser
from lib import configuration
import logging
log = logging.getLogger('fabric.fabalicious.plugins')

def loadPlugins(categories_filter):
  from yapsy.PluginManager import PluginManager
  localPluginsPath = configuration.getSetting("customPlugins.path", '.tools/fabalicious/plugins')
  plugin_dirs = [
    configuration.getBaseDir() + '/' + localPluginsPath,
    configuration.getBaseDir() + '/.fabalicious',
    expanduser("~") + '/.fabalicious/plugins',
    configuration.getRooDir() + '/plugins',
  ]

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


def getTasks():
  try:
    __import__('imp').find_module('yapsy')
    from task import ITaskPlugin
    log.debug('Load Tasks plugins')
    return loadPlugins({ "Task": ITaskPlugin })

  except ImportError:
    log.warning('Custom plugins disabled, as yapsy is not installed!')
    return {}


def getMethods():
  try:
    __import__('imp').find_module('yapsy')
    from method import IMethodPlugin
    log.debug('Load Method plugins')
    return loadPlugins({ "Method": IMethodPlugin })

  except ImportError:
    log.warning('Custom plugins disabled, as yapsy is not installed!')
    return {}
