# How does fabalicious work in two sentences

Fabalicious uses a configuration file with a list of hosts and `ssh` and optionally tools like `composer`, `drush`, `git`, `docker` or custom scripts to run common tasks on remote machines. It is slightly biased to drupal-projects but it works for a lot of other types of projects.

Fabalicious is using [fabric](http://www.fabfile.org) to run tasks on remote machines. The configuration-file contains a list of hosts to work on. Some common tasks are:

 * deploying new code to a remote installation
 * reset a remote installation to its defaults.
 * backup/ restore data
 * copy data from one installation to another
 * optionally work with our docker-based development-stack [multibasebox](https://github.com/factorial-io/multibasebox)

# Table of Contents

  * [How does fabalicious work in two sentences](#how-does-fabalicious-work-in-two-sentences)
  * [Table of Contents](#table-of-contents)
  * [Installation of needed dependencies](#installation-of-needed-dependencies)
  * [Installation of fabalicious](#installation-of-fabalicious)
  * [A simple configuration\-example](#a-simple-configuration-example)
  * [Running fabalicious](#running-fabalicious)
  * [Tasks](#tasks)
    * [Some Background](#some-background)
    * [List of available tasks](#list-of-available-tasks)
    * [config](#config)
    * [list](#list)
    * [about](#about)
    * [getProperty](#getproperty)
    * [version](#version)
    * [deploy](#deploy)
    * [reset](#reset)
    * [backup](#backup)
    * [backupDB](#backupdb)
    * [listBackups](#listbackups)
    * [restore](#restore)
    * [getBackup](#getbackup)
    * [copyFrom](#copyfrom)
    * [copyDBFrom](#copydbfrom)
    * [copyFilesFrom](#copyfilesfrom)
    * [drush](#drush)
    * [drupalconsole](#drupalconsole)
    * [getFile](#getfile)
    * [putFile](#putfile)
    * [getSQLDump](#getsqldump)
    * [restoreSQLFromFile](#restoresqlfromfile)
    * [script](#script)
    * [docker](#docker)
      * [copySSHKeys](#copysshkeys)
      * [startRemoteAccess](#startremoteaccess)
      * [waitForServices](#waitforservices)

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

    ```shellshell
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

# Running fabalicious

To execute a task with the help of fabalicious, just

```shell
cd <your-project-folder>
fab config:<your-config-key> <task>
```

This will read your fabfile.yaml, look for `<your-config-key>` in the host-section and run the task <task>

# Tasks

## Some Background

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

```yaml
needs:
  - git
  - ssh
  - drush
  - files
```

Have a look at the file-format documentation for more info.

## List of available tasks


You can get a list of available commands with

```shell
fab --list
```

## config

```shell
fab config:<your-config>
```

This is one of the most fundamental commands fabalicious provides. This will lookup `<your-config>` in the `hosts`-section of your `fabfile.yaml` and feed the data to `fabric` so it can connect to the host.

## list

```shell
fab list
```

This task will list all your hosts defined in your `hosts`-section of your `fabfile.yaml`.

## about

```shell
fab config:<your-config> about
```

will display the configuration of host `<your-config>`.


## getProperty

```shell
fab config:<your-config> getProperty:<name-of-property>
```

This will print the property-value to the console. Suitable if you want to use fabalicious from within other scripts.

**Examples**
* `fab config:mbb getProperty:host` will print the hostname of configuration `mbb`.
* `fab config:mbb getProperty:docker/tag` will print the tag of the docker-configuration of `mbb`.


## version

```shell
fab config:<your-config> version
```

This command will display the installed version of the code on the installation `<your-config>`.

**Available methods**:
* `git`. The task will get the installed version via `git describe`, so if you tag your source properly (hint git flow), you'll get a nice version-number.

**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.

## deploy

```shell
fab config:<your-config> deploy
fab config:<your-config> deploy:<branch-to-deploy>
```

This task will deploy the latest code to the given installation. If the installation-type is not `dev` or `test` the `backupDB`-task is run before the deployment starts. If `<branch-to-deploy>` is stated the specific branch gets deployed.

After a successfull deployment the `reset`-taks will be run.

**Available methods:**
* `git` will deploy to the latest commit for the given branch defined in the host-configuration. Submodules will be synced, and updated.

**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.


## reset

```shell
fab config:<your-config> reset
```

This task will reset your installation

**Available methods:**
* `composer` will run `composer install` to update any dependencies before doing the reset
* `drush` will
  * set the site-uuid from fabfile.yaml (drupal 8)
  * revert features (drupal 7) / import the configuration `staging` (drupal 8),
  * run update-hooks
  * enable a deployment-module if any stated in the fabfile.yaml
  * and does a cache-clear.
  * if your host-type is `dev` and `withPasswordReset` is not false, the password gets reset to admin/admin


**Configuration:**
* your host-configuration needs a `branch`-key stating the branch to deploy.
* your configuration needs a `uuid`-entry, this is the site uuid (drupal 8). You can get the site-uuid via `drush cget system.site`

**Examples:**
* `fab config:mbb reset:withPasswordReset=0` will reset the installation and will not reset the password.


## backup

```shell
fab config:<your-config> backup
```

This command will backup your files and database into the specified `backup`-directory. The file-names will include configuration-name, a timestamp and the git-SHA1. Every backup can be referenced by its filename (w/o extension) or, when git is abailable via the git-commit-hash.

**Available methods:**
* `git` will prepend the file-names with a hash of the current revision.
* `files` will tar all files in the `filesFolder` and save it into the `backupFolder`
* `drush` will dump the databases and save it to the `backupFolder`

**Configuration:**
* your host-configuration will need a `backupFolder` and a `filesFolder`


## backupDB

```shell
fab config:<your-config> backupDB
```

This command will backup only the database. See the task `backup` for more info.


## listBackups

```shell
fab config:<your-config> listBackups
```

This command will print all available backups to the console.


## restore

```shell
fab config:<your-config> restore:<commit-hash|file-name>
```

This will restore a backup-set. A backup-set consists typically of a database-dump and a gzupped-file-archive. You can a list of candidates via `fab config:<config> listBackups`

**Available methods**
* `git` git will checkout the given hash encoded in the filename.
* `files` all files will be restored. An existing files-folder will be renamed for safety reasons.
* `drush` will import the database-dump.


## getBackup

```shell
fab config:<config> getBackup:<commit-hash|file-name>
```

This command will copy a remote backup-set to your local computer into the current working-directory.

**See also:**
* restore
* backup


## copyFrom

```shell
fab config:<dest-config> copyFrom:<source-config>
```

This task will copy all files via rsync from `source-config`to `dest-config` and will dump the database from `source-config` and restore it to `dest-config`. After that the `reset`-task gets executed. This is the ideal task to copy a complete installation from one host to another.

**Available methods**
* `ssh` will create all necessary tunnels to access the hosts.
* `files` will rsync all new and changed files from source to dest
* `drush` will dump the database and restore it on the dest-host.


## copyDBFrom

```shell
fab config:<dest-config> copyDBFrom:<source-config>
```

Basically the same as the `copyFrom`-task, but only the database gets copied.


## copyFilesFrom

```shell
fab config:<dest-config> copyFileFrom:<source-config>
```

Basically the same as the `copyFrom`-task, but only the new and updated files get copied.


## drush

```shell
fab config:<config> drush:<drush-command>
```

This task will execute the `drush-command` on the remote host specified in <config>. Please note, that you'll have to quote the drush-command when it contains spaces. Signs should be excaped, so python does not interpret them.

**Available methods**
* Only available for the `drush`-method

**Examples**
* `fab config:staging drush:"cc all"`
* `fab config:local drush:fra`


## drupalconsole

This task will execute a drupal-console task on the remote host. Please note, that you'll have to quote the command when it contains spaces. There's a special command to install the drupal-console on the host: `fab config:<config> drupalconsole:install`

**Available methods**
* Only available for the `drupalconsole`-method

**Examples**
* `fab config:local drupalconsole:cache:rebuild`
* `fab config:local drupalconsole:"generate:module --module helloworld"`


## getFile

```shell
fab config:<config> getFile:<path-to-remote-file>
```

Copy a remote file to the current working directory of your current machine.


## putFile

```shell
fab config:<config> putFile:<path-to-local-file>
```

Copy a local file to the tmp-folder of a remote machine.

**Configuration**
* this command will use the `tmpFolder`-host-setting for the destination directory.


## getSQLDump

```shell
fab config:<config> getSQLDump
```

Get a current dump of the remote database and copy it to the local machine into the current working directory.

**Available methods**
* currently only implemented for the `drush`-method


## restoreSQLFromFile

```shell
fab config:<config> restoreSQLFromFile:<path-to-local-sql-dump>
```

This command will copy the dump-file `path-to-local-sql-dump` to the remote machine and import it into the database.

**Available methods**
* currently only implemented for the `drush`-method


## script

```shell
fab config:<config> script:<script-name>
```

This command will run costum scripts on a remote machine. You can declare scripts globally or per host. If the `script-name` can't be found in the fabfile.yaml you'll get a list of all available scripts.

Additional arguments get passed to the script. You'll have to use the python-syntax to feed additional arguments to the script. See the examples.

**Examples**
* `fab config:mbb script`. List all available scripts for configuration `mbb`
* `fab config:mbb script:behat` Run the `behat`-script
* `fab config:mbb script:behat,--name="Login feature",--format=pretty` Run the behat-test, apply `--name` and `--format` parameters to the script

The `script`-command is rather powerful, have a read about it in the extra section.


## docker

```shell
fab config:<config> docker:<docker-task>
```

The docker command is suitable for orchestrating and administering remote instances of docker-containers. The basic setup is that your host-configuration has a `docker`-section, which contains a `configuration`-key. The `dockerHosts`-section of your fabfile.yaml has a list of tasks which are executed on the "parent-host" of the configuration. Please have a look at the docker-section for more information.

Most of the time the docker-container do not have a public or known ip-address. Fabalicious tries to find out the ip-address of a given instance and use that for communicating with its services.

There are three implicit tasks available:

### copySSHKeys

```shell
fab config:mbb docker:copySSHKeys
```

This will copy the ssh-keys into the docker-instance. You'll need to provide the paths to the files via the three configurations:
* `dockerKeyFile`, the path to the private ssh-key to use.
* `dockerAuthorizedKeyFile`, the path to the file for `authoried_keys`
* `dockerKnownHostsFile`, the path to the file for `known_hosts`

As docker-container do not have any state, this task is used to copy any necessary ssh-configuration into the docker-container, so communication per ssh does not need any passwords.

### startRemoteAccess

```shell
fab config:<config> docker:startRemoteAccess
fab config:<config> docker:startRemoteAccess,port=<port>,publicPort=<public-port>
```

This docker-task will run a ssh-command to forward a local port to a port inside the docker-container. It starts a new ssh-session which will do the forwarding. When finished, type `exit`.

**Examples**
* `fab config:mbb docker:startRemoteAccess` will forward `localhost:8888` to port `80` of the docker-container
* `fab config:mbb docker:startRemoteAccess,port=3306,publicPort=33060` will forward `localhost:33060`to port `3306` of the docker-container

### waitForServices

This task will try to establish a ssh-connection into the docker-container and if the connection succeeds, waits for `supervisorctl status` to return success. This is useful in scripts to wait for any services that need some time to start up. Obviously this task depends on `supervisorctl`.


# the structure of the configuration file

## Overview

The configuration is fetched from the file `fabfile.yaml` and should have the followin structure:

```yaml
name: <the project name>

needs:
  - list of methods

requires: 2.0

dockerHosts:
  docker1:
    ...

hosts:
  host1:
    ...
```

Here's the documentation of the supported and used keys:

### name

The name of the project, it's only used for output.

### needs

List here all needed methods for that type of project. Available methods are:
  * `git` for deployments via git
  * `ssh`
  * `drush7` for support of drupal-7 installations
  * `drush8` for support fo drupal 8 installations
  * `files`
  * `slack` for slack-notifications
  * `docker` for docker-support
  * `composer` for composer support
  * `drupalconsole` for drupal-concole support

**Example for drupal 7**

```yaml
needs:
  - ssh
  - git
  - drush7
  - files
```

**Example for drupal 8 composer based and dockerized**

```yaml
needs:
  - ssh
  - git
  - drush8
  - composer
  - docker
  - files
```


### requires

The file-format of fabalicious changed over time. Set this to the lowest version of fabalicious which can handle the file. Should bei `2.0`

### hosts

Hosts is a list of host-definitions which contain all needed data to connect to a remote host. Here's an example

```yaml
hosts:
  exampleHost:
    host: example.host.tld
    user: example_user
    port: 2233
    password: optionalPassword
    type: dev
    rootFolder: /var/www/public
    gitRootFolder: /var/www
    siteFolder: /sites/default
    filesFolder: /sites/default/files
    backupFolder: /var/www/backups
    supportsInstalls: true|false
    supportsCopyFrom: true|false
    type: dev
    branch: develop
    docker:
      ...
    database:
      ...
    scripts:
      ...
    sshTunnel:
      ..

```

* `host`, `user`, `port` and optionally `password` is used to connect via SSH to the remote machine. Please make sure SSH key forwarding is enabled on your installation. `password` should only used as an exception.
* `type` defines the type of installation. Currently there are four types available:
    * `dev` for dev-installations, they won't backup the databases on deployment
    * `test` for test-installations, similar than `dev`, no backups on deployments
    * `stage` for staging-installations.
    * `live` for live-installations. Some tasks can not be run on live-installations as `install` or as a target for `copyFrom`
    The main use-case is to run different scripts per type, see the `common`-section.
* `branch` the name of the branch to use for deployments, they get ususally checked out and pulled from origin. `gitRootFolder` should be the base-folder, where the local git-repository is. (If not explicitely set, fabalicious uses the `rootFolder`)
* `rootFolder`  the web-root-folder of the installation, typically exposed to the public.
* `backupFolder` the folder, where fabalicious shuld store its backups into
* `siteFolder` is a drupal-specific folder, where the settings.php resides for the given installation. This allows to interact with multisites etc.
* `filesFolder` the path to the files-folder, where user-assets get stored and which should be backed up by the `files`-method
* `tmpFolder` name of tmp-folder, defaults to `/tmp`
* `supportsBackups` defaults to true, set to false, if backups are not supported
* `supportsZippedBackups` defaults to true. Set to false, if database-dumps shouldn't be zipped.
* `supportsInstalls` defaults to false, if set to true, the `install`-task will run on that host.
* `supportsCopyFrom` defaults to false, if set to true, the host can be used as target for `copyFrom`
* `ignoreSubmodules`defaults to true, set to false, if you don't want to update a projects' submodule on deploy.
* `disableKonwonHosts`, `useShell` and `usePty` see section `other`
* `database` the database-credentials the `install`-tasks uses when installing a new installation.
    * `name` the database name
    * `host` the database host
    * `user` the database user
    * `pass` the password for the database user
* `docker` for all docker-relevant configuration. `configuration` is the only required key, all other are optional and used by the docker-tasks. `configuration`should contain the key of the dockerHost-configuration in `dockerHosts`



### dockerHosts

TODO

### common

TODO

### scripts:

TODO

### other

* `deploymentModule` name of the deployment-module the drush-method enables when doing a deploy
* `usePty` defaults to true, set it to false when you can't connect to specific hosts.
* `useShell` defaults to true, set it to false, when you can't connect to specific hosts.
* `disableKnownHosts` defaults to false, set it too true, if you trust every host
* `gitOptions` TODO
* `sqlSkipTables` a list of table-names drush should omit when doing a backup.
*


## Inheritance

Sometimes it make sense to extend an existing configuration or to include configuration from other places from the file-system or from remote locations. There's a special key `inheritsFrom` which will include the yaml found at the location and merge it with the data. This is supported for entries in `hosts` and `dockerHosts` and for the fabfile itself.

If a ``host``, a ``dockerHost`` or the fabfile itself has the key ``inheritsFrom``, then the given key is used as a base-configuration. Here's a simple example:

```yaml
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
```

``example1`` will store the merged configuration from ``default`` with the configuration of ``example1``. ``example2``is a merge of all three configurations: ``example2`` with ``example1`` with ``default``.

```yaml
hosts:
  example1:
    port: 23
    host: localhost
    user: default
  example2:
    port: 23
    host: localhost
    user: example2
```

You can even reference external files to inherit from:

```yaml
hosts:
  fileExample:
    inheritsFrom: ./path/to/config/file.yaml
  httpExapme:
    inheritsFrom: http://my.tld/path/to/config_file.yaml
```

This mechanism works also for the fabfile.yaml / index.yaml itself, and is not limited to one entry:

```yaml
name: test fabfile

inheritsFrom:
  - ./mbb.yaml
  - ./drupal.yaml
```

TODO

# scripts

TODO

# docker integration

TODO
