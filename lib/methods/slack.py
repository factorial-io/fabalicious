from base import BaseMethod
from fabric.api import *
from fabric.colors import green, red
from lib import configuration
import json
import getpass

class SlackMethod(BaseMethod):
  @staticmethod
  def supports(methodName):
    return methodName == 'slack'

  def sendMessage(self, config, type, message):
    if 'slack' not in config:
      return

    slack_config = config['slack']
    if type != 'always' and type not in slack_config['notifyOn']:
      return

    try:
      __import__('imp').find_module('slacker')
      from slacker import Slacker

      slack = Slacker(slack_config['token'])

      # Send a message to #general channel
      username = slack_config['username'] + ' (' + getpass.getuser() + ')'
      version = self.factory.call('git', 'getVersion', config)
      version_link = None

      attachments = [{
        'fallback': message,
        'color': 'good',
        'fields': [
          {
            'title': 'Configuration',
            'short': True,
            'value': config['config_name'],
          },
          {
            'title': 'Branch / Version',
            'short': True,
            'value': config['branch'] + ' / ' + version,
          },
        ]
      }]

      if 'gitWebUrl' in slack_config:
        commit = self.factory.call('git', 'getCommitHash', config)
        commit_link = slack_config['gitWebUrl'].replace('%commit%', commit)
        attachments[0]['fields'].append({
          'title': 'Git',
          'value': commit_link,
        })

      attachments = json.dumps(attachments)

      slack.chat.post_message(slack_config['channel'], message, username=username, attachments=attachments, icon_emoji=slack_config['icon_emoji'])
      print green('Slack-notification sent to %s.' % slack_config['channel'])
    except ImportError:
      print red('Please install slacker on this machine: pip install slacker.')



  def notify(self, config, **kwargs):
    message= kwargs['message']
    print 'Sending message per slack "%s"' % message
    self.sendMessage(config, 'always', message)


  def postflight(self, taskName, config, **kwargs):
    print "check %s " % taskName
    self.sendMessage(config, taskName, 'Task "%s" sucessfully finished!"' % taskName)
