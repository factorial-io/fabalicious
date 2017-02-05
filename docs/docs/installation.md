# Installation of needed dependencies

on Mac OS X:

    brew install python
    pip install fabric
    pip install pyyaml

on Debian/Ubuntu

    apt-get install python-pip
    pip install fabric
    pip install pyyaml

If you want to use the slack-integration, install slacker, but it's optional.

    pip install slacker

Create a file called "fabfile.yaml" and add your hosts to this file. See this file for more information.

# Installation of fabalicious

There are 2 alternative ways to install fabalicious. Because of historic reasons we install fabalicious into the folder `_tools/fabalicious`

1. Clone this repository, or add this repository as a submodule.

    ```shell
    mkdir _tools/fabalicious
    git submodule add https://github.com/factorial-io/fabalicious.git _tools/fabalicious
    ln -s _tools/fabalicious/fabfile.py fabfile.py
    ```

2. If you are using composer you can add fabalicious as a dependency

    ```shell
    composer require factorial/fabalicious 2.*
    ln -s _tools/fabalicious/fabfile.py fabfile.py
    ```

3. Run `fab --list`, this should give you a list of available commands.
4. Create a configuration file called `fabfile.yaml`

# A simple configuration-example

```yaml
name: My awesome project

# We'll need fabalicious >= 2.0
requires: 2.0

# We need git and ssh, there are more options
needs:
  - ssh
  - git

# Our list of host-configurations
hosts:
  dev:
    host: myhost.dev
    user: root
    port: 22
    rootFolder: /var/www
    filesFolder: /var/www
    siteFolder: /var/www
    backupFolder: /var/backups
```

For more infos about the file-format have a look at the file-format-section.

