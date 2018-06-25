# Extending fabalicious

You can write custom tasks and methods in python and use it from inside fabalicious.

## Requirements

You need the python library `yapsy`, install it via
```
pip install yapsy
```

## Discovery of plugins

The plugin-resolver will look into the following folders to find tasks and methods:

```
<project_folder>/.fabalicious/plugins
<user-folder>/.fabalicious/plugins
<fabalicious-folder>/plugins
```

## Structure of a plugin

A plugin consists of 2 files, an info-file `<plugin>.yapsy-plugin` and the implementation at `<plugin>.py`

## A custom task

Here's an example for a custom task:

#### foo.yapsy-plugin:

```
[Core]
Name = Foo
Module = foo

[Documentation]
Author = Shibin Das
Version = 0.1
Website = http://www.factorial.io
Description = Foo Plugin
```

#### foo.py:

```python
import logging
log = logging.getLogger('fabric.fabalicious.foo')
from lib.plugins.task import ITaskPlugin

class Foo(ITaskPlugin):
  aliases = ['foo','foobar']
  def run(self):
    log.info('Foobar runs...')
```

Custom tasks need to inherit from `ITaskPlugin` and implement the `run`-method.

## A custom method

Here's an example of a custom method:

#### bar.yapsy-plugin:

```
[Core]
Name = bar
Module = bar

[Documentation]
Author = Stephan Huber
Version = 0.1
Website = http://www.factorial.io
Description = Bar method
```

#### bar.py

```python
import logging
log = logging.getLogger('fabric.fabalicious.bar')
from lib.plugins.method import IMethodPlugin

from fabric.api import *
from lib import configuration
from lib.utils import validate_dict
from lib.configuration import data_merge

class BarMethod(IMethodPlugin):
  @staticmethod
  def supports(methodName):
    return methodName == 'bar'

  def preflight(self, task, config, **kwargs):
    log.info('bar is preflighting task %s' % task)
```

The custom method needs to inherit from `IMethodPlugin` and must implement the static method `supports`. Have a look into the `BaseMethod`-class or any other method to get an idea how to implement your custom method.

To use your custom method, just add its name as a `needs` in fabfile.yaml, e.g.

```
needs:
  - git
  - ssh
  - bar
```
