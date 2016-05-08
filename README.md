# fabalicious -- factorial's deployment scripts

## How does fabalicious work in two sentences

Fabalicious uses a configuration file with a list of hosts and `ssh` and optionally tools like `composer`, `drush`, `git`, `docker` or custom scripts to run common tasks on remote machines. It is slightly biased to drupal-projects but it works for a lot of other projects.

Fabalicious is using [fabric](http://www.fabfile.org) to run tasks on remote machines. The configuration-file contains a list of hosts to work on. Some common tasks are:

 * deploying new code to a remote installation
 * reset a remote installation to its defaults.
 * backup/ restore data
 * copy data from one installation to another
 * optionally work with our docker-based development-stack [multibasebox](https://github.com/factorial-io/multibasebox)


## Installation of needed dependencies

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

## Installation of fabalicious

There are 2 alternative ways to install fabalicious. Because of historic reasons we install fabalicious into the folder `_tools/fabalicious`

1. Clone this repository, or add this repository as a submodule.

    ```
    mkdir _tools/fabalicious
    git submodule add https://github.com/factorial-io/fabalicious.git _tools/fabalicious
    ln -s _tools/fabalicious/fabfile.py fabfile.py
    ```

2. If you are using composer you can add fabalicious as a dependency

    ```
    composer require factorial/fabalicious 2.*
    ln -s _tools/fabalicious/fabfile.py fabfile.py
    ```

3. Run `fab --list`, this should give you a list of available commands.
4. Create a configuration file called `fabfile.yaml`

## A simple configuration-example

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

## Running fabalicious

To execute a task with the help of fabalicious, just

```
cd <your-project-folder>
fab config:<your-config-key> <task>
```

This will read your fabfile.yaml, look for `<your-config-key>` in the host-section and run the task <task>

## List of commands

### Background

Fabalicious provides a set of so-called methods which implement all listed functionality. The following methods are available:

* git
* ssh
* drush
* composer
* files
* docker
* drupalconsole
* slack

You declare your needs in the fabfile.yaml with the key `needs`, e.g.

```
needs:
  - git
  - ssh
  - drush
  - files
```

Have a look at the file-format documentation for more info.

### List of commands

Here's a list of available commands

You can get a list of available commands with

```
fab --list
```

### config

```
fab config:<your-config>
```

This is one of the most fundamental commands fabalicious provides. This will lookup `<your-config>` in the `hosts`-section of your `fabfile.yaml` and feed the data to `fabric` so it can connect to the host.

### list

```
fab list
```

This task will list all your hosts defined in your `hosts`-section of your `fabfile.yaml`.

### about

```
fab config:<your-config> about
```

will display the configuration of host `<your-config>`.


### getProperty

```
fab config:<your-config> getProperty:<name-of-property>
```

This will print the property-value to the console. Suitable if you want to use fabalicious from within other scripts.

**Examples**
* `fab config:mbb getProperty:host` will print the hostname of configuration `mbb`.
* `fab config:mbb getProperty:docker/tag` will print the tag of the docker-configuration of `mbb`.


### version

```
fab config:<your-config> version
```

This command will display the installed version of the code on the installation `<your-config>`.

**Available methods**:
* `git`. The task will get the installed version via `git describe`, so if you tag your source properly (hint git flow), you'll get a nice version-number.

**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.

### deploy

```
fab config:<your-config> deploy
fab config:<your-config> deploy:<branch-to-deploy>
```

This task will deploy the latest code to the given installation. If the installation-type is not `dev` or `test` the `backupDB`-task is run before the deployment starts. If `<branch-to-deploy>` is stated the specific branch gets deployed.

After a successfull deployment the `reset`-taks will be run.

**Available methods:**
* `git` will deploy to the latest commit for the given branch defined in the host-configuration. Submodules will be synced, and updated.

**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.


### reset

```
fab config:<your-config> reset
```

This task will reset your installation

**Available methods:**
* `composer` will run `composer install` to update any dependencies before doing the reset
* `drush` will
  * revert features (drupal 7) / import the configuration (drupal 8),
  * run update-hooks
  * enable a deployment-module if any stated in the fabfile.yaml
  * and does a cache-clear.
  * if your host-type is `dev` and `withPasswordReset` is not false, the password gets reset to admin/admin


**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.

**Examples:**
* `fab config:mbb reset:withPasswordReset=0` will reset the installation and will not reset the password.


### backup

```
fab config:<your-config> backup
```

This command will backup your files and database into the specified `backup`-directory. The file-names will include configuration-name, a timestamp and the git-SHA1. Every backup can be referenced by its filename (w/o extension) or, when git is abailable via the git-commit-hash.

**Available methods:**
* `git` will prepend the file-names with a hash of the current revision.
* `files` will tar all files in the `filesFolder` and save it into the `backupFolder`
* `drush` will dump the databases and save it to the `backupFolder`

**Configuration:**
* your host-configuration will need a `backupFolder` and a `filesFolder`

### listBackups

```
fab config:<your-config> listBackups
```

This command will print all available backups to the console.

### restore

```
fab config:<your-config> restore:<commit-hash|file-name>



----------------------------------------------
Obsolete:

## Usage

List all configurations:

    cd <where-your-fabfile-is>
    fab list

List a specific configuration:

    cd <where-your-fabfile-is>
    fab about:hostA

List all available tasks:

    cd <where-your-fabfile-is>
    fab --list

Run a task

    cd <where-your-fabfile-is>
    fab config:hostA <task-name>


##Documentation

You'll find an extensive documentation in our [wiki](https://github.com/factorial-io/fabalicious/wiki)

##


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
* `installBehat`: install behat, the configuration needs a setting for `behat:install` which gets called to install behat at.
* `drush:<command>`: run drush command on given host. Add '' as needed, e.g. fab config:local "drush:cc all"
* `docker:<subtask>`: runs a set of scripts on the host-machine to control docker-instances.
* `copySSHKeysToDocker`: copies stored ssh-keys into a docker-image. You'll need to set `dockerKeyFile`. If there's a setting for `dockerAuthorizedKeyFile` the authorized_key-file will also copied into the docker. This will help with docker-to-docker-communication via SSH.
* `updateDrupalCore:<version=x>`: This task will create a new branch, download the latest stable release from drupal, and move all files to your webRoot. After that you can review the new code, commit it and marge it into your existing branch. Why not use drush for this? In my testings it didn't work reliable, sometimes the update went smooth, sometimes it doesn't do anything.
* `restoreSQLFromFile:<file-name>`: will copy file-name to the remote host and import it via drush.
* `ssh`: create a remote shell.
* `putFile:<filename>` copy a file to the remote host into the tmp-folder.
* `getFile:<filename>:localPath=<path>` copy a file from the remote host to the local host at `<path>`.
* `notify:<message>` send a message via slack or other method.
* `script:<scriptName>` run a script declared under the global `scripts`-section


##fabfile.yaml

    name: The name of your project

    #optional
    requires: the required version of fabalicous to handle this configuration, e.g. 0.18.2

    needs: a list of needed methods. available are git, drush7, drush8, files, ssh, slack, composer. Defaults to [git, drush7, files, ssh]

    #optional
    deploymentModule: the name of your drupal deployment-module/Users/stephan/Documents/dev/web/multibasebox/projects/test/_tools/fabalicious/README.md

    # common commands are executed when resetting/deploying an installation,
    # for all hosts. if 'useForDevelopment' is set, then 'development' is used
    common:
      dev:
        # custom commands to run for development-installations, e.g:
        - "drush vset -y --exact devel_rebuild_theme_registry TRUE"
      stage:
        # custom commands to run for all installations of type 'prod', e.g:
        - "drush dis -y devel"
      prod:
        # custom commands to run for installations of type 'prod'

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

    # Integration with slack. Note that you can set these variables also per host
    # they are get merged, with precedence of host-variables.
    # notifyOn has a list of tasks which sends a notification to slack
    # you'll need to install the slacker-modul for python.

    slack:
      token: <your-slack-api-token>
      channel: <channel-name>
      username: <username, optional>
      icon_emoji: <name of icon, optional>
      gitWebUrl: <URL to the git-web-repository, '%commit%' gets replaced with the current version, optional>
      nofifyOn:
        - backup
        - reset
        - deploy
        - always

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

    # Scripts can contain any number of scripts, which can be called via the script-task
    scripts:
      scriptA:
        - echo "foo"
        - echo "bar"
      scriptB:
        - echo "FooBar"

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
        # type of installation, required, defaults to prod
        type: <dev|stage|prod>
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
          host: <database-host, defaults to "localhost">

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
