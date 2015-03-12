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

    #optional
    requires: the required version of fabalicous to handle this configuration, e.g. 0.18.2

    #optional
    deploymentModule: the name of your drupal deployment-module/Users/stephan/Documents/dev/web/multibasebox/projects/test/_tools/fabalicious/README.md

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

    # optional, a list of tables to skip, when dumping to sql,
    # set to False, if you want to dump all tables. If nothing is set,
    # fabalicious will skip common drupal cache-tables.
    sqlSkipTables:
      - cache
      - views_cache

    # hide specific output from the console. The standard is to hide all output and
    # show the output, when a command fails. For debugging purposes you can enable
    # more output like this:
    hideOutput: []

    # The default settings which can be overwritten:
    hideOutput:
      - running
      - stdout
      - stderr
      - warnings

    # custom parameters for git-commands (currently only pull supported)
    # if no custom parameters are set '--rebase' and '--no-edit' are used
    # here you can define the defaults for all configurations
    # you can overwrite them in the single host-configs, if needed
    gitConfig:
      pull:
        - --rebase
        - --no-edit
    # path to a private key which should be used for a docker-image, see task
    # copySSHKeyToDocker
    dockerKeyFile: _tools/ssh-key/docker-root-key

    # path to a authorized_keys-file which should be used for a docker-image,
    # see task copySSHKeyToDocker
    dockerAuthorizedKeyFile: _tools/ssh-key/authorized_keys

    # dockerHosts is a list of hosts which hosts docker-installations
    # hosts can reference one of this configurations via docker/configuration

    dockerHosts:
      hostA:
        host: <host>
        user: <user>
        port: <port>
        rootFolder: <path-where-your-docker-stuff-resides>
        requires: optional, the required version of fabalicous to handle this configuration, e.g. 0.18.2

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
        requires: optional, the required version of fabalicous to handle this configuration, e.g. 0.18.2

        # if you are using basebox for setting up a vagrant-setup, specify the
        # ip here
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

          # if you have multiple ssh-tunnel-configurations make sure your
          # local-port is unique accross the file!
          localPort: <localPort>

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

        behat:
          run: <command-line to run behat>
          install:
            - <command to install behat>
            - <command to install behat>

        # the commands in reset, deplayPrepare and deploy may use the data of
        # the configuration via the placeholder '%key%', e.g. '%sitesFolder%'
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

        # add custom parameters to git-commands:
        gitOptions:
          pull:
            - <parameter 1>
            - <parameter 2>
            # e.g.:
            - --rebase

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
* `backup`: tar all files, dump the database and copy them to the backup-directory.
* `backupDB`: backup the DB tp the backups-directory only
* `listBackups`: list all previously made backups
* `restore:<commit|partial-filename>` will restore files and/or DB from given commit or partial filename and reset git's HEAD to given revision.
* `deploy`: update the installation by pulling the newest source from git and running the reset-task afterwards
* `copyFrom:<source-host>`: copies all files from `filesFolder` at source-host to target host, and imports a sql-dump from source-host.
* `copyDBFrom:<source-host>`: copies only the DB from the source-host
* `copyFilesFrom:<source-host>`: copies only the files from the source-host
* `install:<distribution=minimal>,<ask=True>`: will install a database in the docker-container. Works currently only when `supportsInstall=true` and `useForDevelopment=true`. Needs an additional host-setting: `database`-dictionary. If `hasDrush=true` the code will install drupal with profile minimal, if the optional distribution-parameter is not set.  This task will overwrite your settings.php-file and databases, so be prepared! This task has two optional parameter: you can install another distribution when setting ``distribution`` according to your needs. If you set ``ask`` to (0|false) there will be no confimration dialog.
* `behat:<name="Name of feature",format="pretty", out="", options="">`: run behat tests, the configuration needs a setting for `behat:run` which gets called to run the tests. You can add command-line-options to the command, the most used (name, format and out) are mirrored by fabalicious, as escaping all the commas is cumbersome.
* `installBehat`: install behat, the configuration needs a setting for `behat:install` which gets called to install behat
at.
* `drush:<command>`: run drush command on given host. Add '' as needed, e.g. fab config:local "drush:cc all"
* `docker:<subtask>`: runs a set of scripts on the host-machine to control docker-instances.
* `copySSHKeysToDocker`: copies stored ssh-keys into a docker-image. You'll need to set `dockerKeyFile`. If there's a setting for `dockerAuthorizedKeyFile` the authorized_key-file will also copied into the docker. This will help with docker-to-docker-communication via SSH.
* `updateDrupalCore:<version=x>`: This task will create a new branch, download the latest stable release from drupal, and move all files to your webRoot. After that you can review the new code, commit it and marge it into your existing branch. Why not use drush for this? In my testings it didn't work reliable, sometimes the update went smooth, sometimes it doesn't do anything.
* `restoreSQLFromFile:<file-name>`: will copy file-name to the remote host and import it via drush.
* `ssh`: create a remote shell.
* `putFile:<filename>` copy a file to the remote host into the tmp-folder.


## Advanced topics

### Storing your hosts and dockerHosts configuration in separate files

Instead of storing all your information in one fabfile.yaml you can create a folder named ``fabalicious`` and store global information in ``index.yaml``, dockerHosts-configuration in ``dockerHosts`` and host-configuration in the folder ``hosts``. The filename acts as the key for the included configuration. Here's an example:

    fabalicious
    ├── dockerHosts
    │   ├── default.yaml
    │   ├── local.yaml
    │   ├── mbb.yaml
    │   └── dev-server.yaml
    ├── hosts
    │   ├── local.yaml
    │   ├── mbb.yaml
    │   ├── dev.host.server2.de.yaml
    │   ├── stage.host.server2.de.yaml
    │   └── live.host.server2.de.yaml
    └── index.yaml

dockerHosts has 4 configurations: ``default``, ``local``, ``mbb``, and ``dev-server``. Hosts as 5 configurations named ``local``, ``mbb``, ``dev.host.server2.de``, ``stage.host.server2.de``, and ``live.host.server2.de.yaml``.

Here's an example of ``local.yaml``: (Note the missing key)

    host: drupal.dev
    port: 222
    user: root
    password: root
    rootFolder: /var/www
    siteFolder: /sites/default
    filesFolder: /sites/default/files
    backupFolder: /var/www/backups
    useForDevelopment: true
    branch: develop
    hasDrush: true
    supportsInstalls: true
    vagrant:
      ip: 33.33.33.21
    docker:
      name: drupal
      configuration: local
    database:
      name: drupal_cms
      user: root
      pass: admin

If your fabalicious-folder is part of your web-directory, add an ``.htaccess``-file to your fabalicious-folder:

    <FilesMatch ".(yaml|yml)$">
      deny from all
    </FilesMatch>


### Include dockerHosts-configuration from outside the fabfile.yaml/ fabalicious-folder

To prevent copy-/pasting configuration from one project to another you can reference files from outside your fabalicious-folder/ -file. You can reference files from your file-system (relative to the location of your fabfile.yaml / fabalicious-folder) or remote-files via http/https.

Reference the external file in your host-configuration via

    mbb:
      host: ...
      ...
      docker:
        configuration: ./path/to/the/external/config-file.yaml

or

    mbb:
      host: ...
      ...
      docker:
        configuration: ../../../global-config/path/to/the/external/config-file.yaml

or

    mbb:
      host: ...
      ...
      docker:
        configuration: http://external.host.tld/path/to/the/external/config-file.yaml

### Inheritance

Besides including external files there's another mechanism to include configuration-data: Inheritance.
If a ``host``, a ``dockerHost`` or the fabfile itself has the key ``inheritsFrom``, then the given key is used as a base-configuration. Here's a simple example:

    hosts:
      default:
          port: 22
          host: localhost
          user: default
      example1:
          inheritsFrom: default
          port: 23
      example2:
          inheritsFrom: example1
          user: example2

``example1`` will store the merged configuration from ``default`` with the configuration of ``example1``. ``example2``is a merge of all three configurations: ``example2`` with ``example1`` with ``default``.

    hosts:
      example1:
        port: 23
        host: localhost
        user: default
      example2:
        port: 23
        host: localhost
        user: example2


You can even reference external files to inherit from:

    hosts:
      fileExample:
        inheritsFrom: ./path/to/config/file.yaml
      httpExapme:
        inheritsFrom: http://my.tld/path/to/config_file.yaml

This mechanism works also for the fabfile.yaml / index.yaml itself, and is not limited to one entry:

    name: test fabfile

    inheritsFrom:
      - ./mbb.yaml
      - ./drupal.yaml
