import yaml
import re
from lib import configuration


def getTemplate(configName):
  settings = configuration.get_all_configurations()
  config = False

  if not configName:
    config = configuration.current()
  else:
    if configName in settings['hosts']:
      config = configuration.get(configName)

  if config and 'blueprint' in config:
    return config['blueprint']

  if config and 'docker' in config:
    docker_config_name = config['docker']['configuration']
  else:
    docker_config_name = configName

  if docker_config_name:
    docker_config = configuration.getDockerConfig(docker_config_name)
    if docker_config and 'blueprint' in docker_config:
      return docker_config['blueprint']

  if settings and 'blueprint' in settings:
    return settings['blueprint']

  return False


def slugify(str, replacement=''):
  return re.sub('(\s|_|\-|\/)', replacement, str)



def apply_helper(value, replacements):
  if isinstance(value, dict):
    result = {}
    for key, val in value.items():
      result[key] = apply_helper(val, replacements)
    return result

  elif hasattr(value, "__len__") and not hasattr(value, 'strip'):
    result = []
    for list_value in value:
      result.push(apply_helper(list_value, replacements))
    return result

  else:
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    result = pattern.sub(lambda x: replacements[x.group()], value)

    return result




def apply(identifier, template):
  project_name = configuration.getSettings('name', 'unknown')

  replacements = {}
  replacements['%identifier%'] = identifier
  replacements['%slug%'] = slugify(identifier)
  replacements['%slug-with-hyphen%'] = slugify(identifier, replacement='-')
  replacements['%project-identifier%'] = project_name
  replacements['%project-slug%'] = slugify(project_name)
  replacements['%project-slug-with-hypen%'] = slugify(project_name, replacement='-')

  result = apply_helper(template, replacements)
  return result


def output(config):
  data = { 'hosts': { config['configName']: config } }
  print yaml.dump(data, default_flow_style=False, default_style='')

