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

On systems with a non-bash environment like lshell try the following settings in your fabfile.yaml

    useShell: false
    usePty: false


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

    # optional, defaults to true
    useShell: <boolean>
    # optional, defaults to true
    usePty: <boolean>

    # dockerHosts is a list of hosts which hosts docker-installations
    # hosts can reference one of this configurations via docker/configuration

    dockerHosts:
      hostA:
        host: <host>
        user: <user>
        port: <port>
        rootFolder: <path-where-your-docker-stuff-resides>

        # you can add as many subtasks you want to control your docker instances.
        # you can use the configuration of your hosts-part with %varname% as pattern,
        # e.g. %name%. You can even reference some variables of the docker-guest-
        # configuration via %guest.<name>%, e.g. %guest.branch%
        tasks:
          start:
            - docker start %name%
          stop:
            - docker stop %name%
          create:
            - git clone https://github.com/test/test.git %folder%
            - cd %folder% && git checkout %guest.branch%
            - docker build  -t %name%/%tag% %folder%
            - docker run --name %name% %name%/%tag%

          destroy:
            # you can even run other docker-tasks via run_task(<task_name>)
            - run_task(stop)
            - docker rm %name%
            - docker rmi %name/%tag%
            - rm -rf %folder%


      hostB:
        # you can "include" the configuration of another host via inheritsFrom
        # and overwrite only differing parameters
        inheritsFrom: <key>
        host: <another-host>



    hosts:
      hostA:
        host: <host>
        port: <port>
        user: <your-ssh-user>

        # if you are using basebox for setting up a vagrant-setup, specify the ip here
        # see https://github.com/MuschPusch/basebox
        ip: <your-ip-address, optional>

        # if you can't reacht your host directly, you can use a ssh-tunnel,
        # please note that your host should be localhost and port the localPort of
        # your sshTunnel-configuration
        sshTunnel:
          bridgeUser: <bridgeUser>
          bridgeHost: <bridgeHost>
          bridgePort: <bridgePort>
          destHost: <destHost>
          destPort: <destPort>

          # if you have multiple ssh-tunnel-configurations make sure your local-port is unique accross the file!
          localPort: <localPort>

          # if you want to deploy into docker container you can use a docker-
          # container-name, the script will use docker inspect to get the container's
          # ip-address
          destHostFromDockerContainer: <docker-container-name>

          # when accessing docker-container via tunnels and ssh it may be necessary
          # to disable strictHostKeyChecking over the tunnel
          strictHostKeyChecking: <boolean, optional defaults to true


        rootFolder: <absolute-path-to-your-webroot>
        # optional and defaults to rootFolder
        gitRootFolder: <absolute-path-to-your-gitroot>
        # optional and defaults to /tmp/
        tmpFolder: <absolute-path-to-your-tmp>
        sitesFolder: <relative-path-to-your-sites-folder>
        filesFolder: <relative-path-to-yout-files-folder>
        backupFolder: <absolute-path-where-backup-should-be-stored>

        # optional and defaults to true
        hasDrush: <boolean>
        # optional and defaults to false
        useForDevelopment: <boolean>
        # optional and defaults to false
        ignoreSubmodules: <boolean>
        # optional and defaults to true
        supportsBackups: <boolean>
        # optional and defaults to true
        supportsCopyFrom: <boolean>
        # optional and defaults to true
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

        # configuration needed for the install-task:
        # optional and defaults to false
        supportsInstalls: <boolean>
        database:
          user: <database-user>
          pass: <database-password>
          name: <name-of-database>

        # docker-specific vars
        # you can add any vars to this section, you can use it in your
        # docker-scripts with %varname%, e.g. %name%
        docker:
          name: <docker-name, required>
          configuration: <name-of-configuration, required>


      hostB:
        # you can "include" the configuration of another host via inheritsFrom
        # and overwrite only differing parameters
        inheritsFrom: <key>
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
* `docker:<subtask>`: runs a set of scripts on the host-machine to control docker-instances.


