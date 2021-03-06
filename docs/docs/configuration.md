# Structure of the configuration file

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

You can get all host-information including the default values using the fabalicious command `about`:

```shell
fab config:staging about
```

This will print all host configuration for the host `staging`.

Here are all possible keys documented:

* `host`, `user`, `port` and optionally `password` is used to connect via SSH to the remote machine. Please make sure SSH key forwarding is enabled on your installation. `password` should only used as an exception.
* `type` defines the type of installation. Currently there are four types available:
    * `dev` for dev-installations, they won't backup the databases on deployment
    * `test` for test-installations, similar than `dev`, no backups on deployments
    * `stage` for staging-installations.
    * `live` for live-installations. Some tasks can not be run on live-installations as `install` or as a target for `copyFrom`
    The main use-case is to run different scripts per type, see the `common`-section.
* `branch` the name of the branch to use for deployments, they get ususally checked out and pulled from origin. `gitRootFolder` should be the base-folder, where the local git-repository is. (If not explicitely set, fabalicious uses the `rootFolder`)
* `rootFolder`  the web-root-folder of the installation, typically exposed to the public.
* `gitRootFolder`  the folder, where the git-repository lies. Defaults to `rootFolder`
* `composerRootFolder` the folder where the composer.json for the project is stored, defaults to `gitRootFolder`.
* `backupFolder` the folder, where fabalicious should store its backups into
* `runLocally` if set to true, all commands are run on the local host, not on a remote host. Good for local development on linux or tools like MAMP.
* `siteFolder` is a drupal-specific folder, where the settings.php resides for the given installation. This allows to interact with multisites etc.
* `filesFolder` the path to the files-folder, where user-assets get stored and which should be backed up by the `files`-method
* `tmpFolder` name of tmp-folder, defaults to `/tmp`
* `supportsBackups` defaults to true, set to false, if backups are not supported
* `supportsZippedBackups` defaults to true. Set to false, if database-dumps shouldn't be zipped.
* `supportsInstalls` defaults to false, if set to true, the `install`-task will run on that host.
* `supportsCopyFrom` defaults to false, if set to true, the host can be used as target for `copyFrom`
* `ignoreSubmodules` defaults to true, set to false, if you don't want to update a projects' submodule on deploy.
* `revertFeatures`, defaults to `True`, when set all features will be reverted when running a reset (drush only)
* `configurationManagement`, an array of configuration-labels to import on `reset`, defaults to `['staging']`. You can add command arguments for drush, e.g. `['staging', 'dev --partial']`
* `disableKnownHosts`, `useShell` and `usePty` see section `other`
* `database` the database-credentials the `install`-tasks uses when installing a new installation.
    * `name` the database name
    * `host` the database host
    * `user` the database user
    * `pass` the password for the database user
    * `prefix` the optional table-prefix to use
* `sshTunnel` Fabalicious supports SSH-Tunnels, that means it can log in into another machine and forward the access to the real host. This is handy for dockerized installations, where the ssh-port of the docker-instance is not public. `sshTunnel` needs the following informations
    * `bridgeHost`: the host acting as a bridge.
    * `bridgeUser`: the ssh-user on the bridge-host
    * `bridgePort`: the port to connect to on the bridge-host
    * `localPort`: the local port which gets forwarded to the `destPort`. If `localPort` is omitted, the ssh-port of the host-configuration is used. If the host-configuration does not have a port-property a random port is used.
    * `destHost`: the destination host to forward to
    * `destHostFromDockerContainer`: if set, the docker's Ip address is used for destHost. This is automatically set when using a `docker`-configuration, see there.
    * `destPort`: the destination port to forward to
* `docker` for all docker-relevant configuration. `configuration` and `name` are the only required keys, all other are optional and used by the docker-tasks.
    * `configuration` should contain the key of the dockerHost-configuration in `dockerHosts`
    * `name` contains the name of the docker-container. This is needed to get the IP-address of the particular docker-container when using ssh-tunnels (see above).



### dockerHosts

`dockerHosts` is similar structured as the `hosts`-entry. It's a keyed lists of hosts containing all necessary information to create a ssh-connection to the host, controlling the docker-instances, and a list of tasks, the user might call via the `docker`-command. See the `docker`-entry for a more birds-eye-view of the concepts.

Here's an example `dockerHosts`-entry:

```yaml
dockerHosts:
  mbb:
    runLocally: false
    host: multibasebox.dev
    user: vagrant
    password: vagrant
    port: 22
    rootFolder: /vagrant
    environment:
      VHOST: %host.host%
      WEBROOT: %host.rootFolder%
    tasks:
      logs:
        - docker logs %host.docker.name%
```

Here's a list of all possible entries of a dockerHosts-entry:

* `runLocally`: if this is set to `true`, all docker-scripts are run locally, and not on a remote host.
* `host`, `user`, `port` and `password`: all needed information to start a ssh-connection to that host. These settings are only respected, if `runLocally` is set to `false`. `port` and `password` are optional.
* `environment` a keyed list of environment-variables to set, when running one of the tasks. The replacement-patterns of `scripts` are supported, see there for more information.
* `tasks` a keyed list of commands to run for a given docker-subtask (similar to `scripts`). Note: these commands are running on the docker-host, not on the host. All replacement-patterns do work, and you can call even other tasks via `execute(<task>, <subtask>)` e.g. `execute(docker, stop)` See the `scripts`-section for more info.

You can use `inheritsFrom` to base your configuration on an existing one. You can add any configuration you may need and reference to that information from within your tasks via the replacement-pattern `%dockerHost.keyName%` e.g. `%dockerHost.host%`.

You can reference a specific docker-host-configuration from your host-configuration via

```yaml
hosts:
  test:
    docker:
      configuration: mbb
```

### common

common contains a list of commands, keyed by task and type which gets executed when the task is executed.

Example:
```yaml
common:
  reset:
    dev:
      - echo "running reset on a dev-instance"
    stage:
      - echo "running reset on a stage-instance"
    prod:
      - echo "running reset on a prod-instance"
  deployPrepare:
    dev:
      - echo "preparing deploy on a dev instance"
  deploy:
    dev:
      - echo "deploying on a dev instance"
  deployFinished:
    dev:
      - echo "finished deployment on a dev instance"
```

The first key is the task-name (`reset`, `deploy`, ...), the second key is the type of the installation (`dev`, `stage`, `prod`, `test`). Every task is prepended by a prepare-stage and appended by a finished-stage, so you can call scripts before and after an actual task. You can even run other scripts via the `execute`-command, see the `scripts`-section.

### scripts

A keyed list of available scripts. This scripts may be defined globally (on the root level) or on a per host-level. The key is the name of the script and can be executed via

```shell
fab config:<configuration> script:<key>
```

A script consists of an array of commands which gets executed sequentially.

An example:

```yaml
scripts:
  test:
    - echo "Running script test"
  test2:
    - echo "Running script test2 on %host.config_name%
    - execute(script, test)
```

Scripts can be defined on a global level, but also on a per host-level.

You can declare default-values for arguments via a slightly modified syntax:

```yaml
scripts:
  defaultArgumentTest:
    defaults:
      name: Bob
    script:
      - echo "Hello %arguments.name%"
```

Running the script via `fab config:mbb script:defaultArgumentTest,name="Julia"` will show `Hello Julia`. Running `fab config:mbb script:defaultArgumentTest` will show `Hello Bob`.

For more information see the main scripts section below.

### other

* `deploymentModule` name of the deployment-module the drush-method enables when doing a deploy
* `usePty` defaults to true, set it to false when you can't connect to specific hosts.
* `useShell` defaults to true, set it to false, when you can't connect to specific hosts.
* `disableKnownHosts` defaults to false, set it too true, if you trust every host
* `gitOptions` a keyed list of options to apply to a git command. Currently only pull is supported. If your git-version does not support `--rebase` you can disable it via an empty array: `pull: []`
* `sqlSkipTables` a list of table-names drush should omit when doing a backup.
* `configurationManagement` a list of configuration-labels to import on `reset`. This defaults to `['staging']` and may be overridden on a per-host basis. You can add command arguments to the the configuration label.

Example:
```yaml
deploymentModule: my_deployment_module
usePty: false
useShell: false
gitOptions:
  pull:
    - --rebase
    - --quiet
sqlSkipTables:
  - cache
  - watchdog
  - session
configurationManagement:
   - staging
   - dev -- partial
```


## Inheritance

Sometimes it make sense to extend an existing configuration or to include configuration from other places from the file-system or from remote locations. There's a special key `inheritsFrom` which will include the yaml found at the location and merge it with the data. This is supported for entries in `hosts` and `dockerHosts` and for the fabfile itself.

If a `host`, a `dockerHost` or the fabfile itself has the key `inheritsFrom`, then the given key is used as a base-configuration. Here's a simple example:

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

`example1` will store the merged configuration from `default` with the configuration of `example1`. `example2` is a merge of all three configurations: `example2` with `example1` with `default`.

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



# Scripts

Scripts are a powerful concept of fabalicious. There are a lot of places where scripts can be called. The `common`-section defines common scripts to be run for specific task/installation-type-configurations, docker-tasks are also scripts which you can execute via the docker-command. And you can even script fabalicious tasks and create meta-tasks.

A script is basically a list of commands which get executed via shell on a remote machine. To stay independent of the host where the script is executed, fabalicious parsed the script before executing it and replaces given variables with their counterpart in the yams file.

## Replacement-patterns

Replacement-Patterns are specific strings enclosed in `%`s, e.g. `%host.port%`, `%dockerHost.rootFolder%` or `%arguments.name%`.

Here's a simple example;

```yaml
script:
  test:
    - echo "I am running on %host.config_name%"
```

Calling this script via

```shell
fab config:mbb script:test
```

will show `I am running on mbb`.

* The host-configuration gets exposes via the `host.`-prefix, so `port` maps to `%host.port%`, etc.
* The dockerHost-configuration gets exposed via the `dockerHost`-prefix, so `rootFolder` maps to `%dockerHost.rootFolder%`
* The global configuration of the yams-file gets exposed to the `settings`-prefix, so `uuid` gets mapped to `%settings.uuid%
* Optional arguments to the `script`-taks get the `argument`-prefix, e.g. `%arguments.name%`. You can get all arguments via `%arguments.combined%`.
* You can access hierarchical information via the dot-operator, e.g. `%host.database.name%`

If fabalicious detects a pattern it can't replace it will abort the execution of the script and displays a list of available replacement-patterns.

## Internal commands

There are currently 3 internal commands. These commands control the flow inside fabalicious:

* `fail_on_error(1|0)` If fail_on_error is set to one, fabalicious will exit if one of the script commands returns a non-zero return-code. When using `fail_on_error(0)` only a warning is displayed, the script will continue.
* `execute(task, subtask, arguments)` execute a fabalicious task. For example you can run a deployment from a script via `execute(deploy)` or stop a docker-container from a script via `execute(docker, stop)`
* `fail_on_missing_directory(directory, message)` will print message `message` if the directory `directory` does not exist.

## Task-related scripts

You can add scripts to the `common`-section, which will called for any host. You can differentiate by task-name and host-type, e.g. create a script which gets called for the task `deploy` and type `dev`.

You can even run scripts before or after a task is executed. Append the task with `Prepare` or `Finished`.

You can even run scripts for specific tasks and hosts. Just add your script with the task-name as its key.

```yaml
host:
  test:
    deployPrepare:
      - echo "Preparing deploy for test"
    deploy:
      - echo "Deploying on test"
    deployFinished:
      - echo "Deployment finished for test"
```

These scripts in the above examples gets executed only for the host `test` and task `deploy`.

## Examples

A rather complex example scripting fabalicious.

```yaml
scripts:
  runTests:
    defaults:
      branch: develop
    script:
      - execute(docker, start)
      - execute(docker, waitForServices)
      - execute(deploy, %arguments.branch%)
      - execute(script, behatInstall)
      - execute(script, behat, --profile=ci --format=junit --format=progress)
      - execute(getFile, /var/www/_tools/behat/build/behat/default.xml, ./_tools/behat)
      - execute(docker, stop)
```

This script will

* start the docker-container,
* wait for it,
* deploys the given branch,
* run a script which will install behat,
* run behat with some custom arguments,
* gets the result-file and copy it to a location,
* and finally stops the container.
