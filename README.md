# fabalicious -- huber's deployment scripts

this fabfile is a special crafted deployment script to help deploy drupal installations across different servers.
It reads a yaml-file called "fabfile.yaml" where all hosts are stored.

##Prerequisites

on Mac OS X:

    brew install python
    pip install fabric
    pip install pyyaml

on Debian/Ubuntu

    apt-get install python-pip
    pip install fabric
    pip install pyyaml


##fabfile.yaml

    name: The name of your project
    deploymentModule: the name of your drupal deployment-module
    # common commands are executed when resetting/deploying an installation,
    # for all hosts. if 'useForDevelopment' is set, then 'development' is used
    common:
      development:
        # custom commands to run for development-installations, e.g:
        - "drush vset -y --exact devel_rebuild_theme_registry TRUE"
      deployment:
        # custom commands to run for all other installations, e.g:
        - "drush dis -y devel"
    hosts:
      hostA:
        host: <host>
        port: <port>
        user: <your-ssh-user>
        # if you can't reacht your host directly, you can use a ssh-tunnel,
        # please note that your host should be localhost and port the localPort of
        # your sshTunnel-configuration
        sshTunnel:
          bridgeUser: <bridgeUser>
          bridgeHost: <bridgeHost>
          bridgePort: <bridgePort>
          destHost: <destHost>
          # if you want to deploy into docker container you can use a docker-
          # container-name, the script will use docker inspect to get the container's
          # ip-address
          destHostFromDockerContainer: <docker-container-name>
          destPort: <destPort>
          localPort: <localPort>
        rootFolder: <absolute-path-to-your-webroot>
        sitesFolder: <relative-path-to-your-sites-folder>
        filesFolder: <relative-path-to-yout-files-folder>
        backupFolder: <absolute-path-where-backup-should-be-stored>
        hasDrush: <boolean>
        useForDevelopment: <boolean>
        ignoreSubmodules: <boolean>
        supportsBackups: <boolean>
        supportsCopyFrom: <boolean>
        supportsInstalls: <boolean>
        supportsZippedBackups: <boolean>
        reset:
          - "first custom reset command"
          - "second custom reset command"
        deployPrepare:
          - "first custom command run before doing a deploy"
          - "second custom command run before doing a deploy"
        deploy:
          - "first custom deploy command"
          - "second custom deploy command"
      hostB:
        ...
## Usage

list all configurations:

    cd <where-your-fabfile-is>
    fab list

list a specific configuration:

    cd <where-your-fabfile-is>
    fab about:hostA

list all available tasks:

    cd <where-your-fabfile-is>
    fab --list

run a task

    cd <where-your-fabfile-is>
    fab config:hostA <task-name>

##Available tasks:

* `version`: get the current version of the source (= git describe)
* `reset`: reset the drupal-installation, clear the caches, run update, reset all features, enable deploy-module and its dependencies
* `backup`: tar all files, dump the database and copy them to the backup-directory. optional parameter: `withFiles=0`, backup db only, w/o files
* `deploy`: update the installation by pulling the newest source from git and running the reset-task afterwards
* `copyFrom:<source-host>`: copies all files from filesFolder at source-host to target host, and imports a sql-dump from source-host.
* `drush:<command>`: run drush command on given host. Add '' as needed, e.g. fab config:local "drush:cc all"
* `install`: will install drupal with profile minimal. Works currently only wehn supportsInstall=true, hasDrush=true and useForDevelopment=true. Needs an additional host-setting 'databaseName'. This task will overwrite your settings.php-file and databases, so be prepared!



