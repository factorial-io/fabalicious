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

## offline

```shell
fab offline config:<your-config> <task>
```

This task will disable remote configuration files. As fabalicious keeps copies of remote configuration-files in `~/.fabalicious` it will try to load the configuration-file from there.

## blueprint

```shell
fab config:<your-config> blueprint:<branch-name>
fab blueprint:<branch-name>,configName=<config-name>
fab blueprint:<branch-name>,configNmae=<config-name>,output=True
```

`blueprint` will try to load a blueprint-template from the fabfile.yaml and apply the input given as `<branch-name>` to the template. This is helpful if you want to create/ use a new configuration which has some dynamic parts like the name of the database, the name of the docker-container, etc.

The task will look first in the host-config for the property `blueprint`, afterwards in the dockerHost-configuration `<config-name>` and eventually in the global namespace. If you wnat to print the generated configuration as yaml, then add `,output=true` to the command. If not, the generated configuration is used as the current configuration, that means, you can run other tasks against the generated configuration.

**Available replacement-patterns** and what they do.

_Input is `feature/XY-123-my_Branch-name`, the project-name is `Example project`_

|  Replacement Pattern                    | value                         |
|-----------------------------------------|-------------------------------|
| **%slug.with-hyphens.without-feature%** | xy-123-my-branch-name         |
| **%slug.with-hyphens%**                 | feature-xy-123-my-branch-name |
| **%project-slug.with-hypens%**          | example-project               |
| **%slug%**                              | featurexy123mybranchname      |
| **%project-slug%**                      | exampleproject                |
| **%project-identifier%**                | Example project               |
| **%identifier%**                        | feature/XY-123-my_Branch-name |
| **%slug.without-feature%**              | xy123mybranchname             |


Here's an example blueprint:

```yaml
blueprint:
  inheritsFrom: http://some.host/data.yaml
  configName: '%project-slug%-%slug.with-hyphens.without-feature%.some.host.tld'
  branch: '%identifier%'
  database:
    name: '%slug.without-feature%_mysql'
  docker:
    projectFolder: '%project-slug%--%slug.with-hyphens.without-feature%'
    vhost: '%project-slug%-%slug.without-feature%.some.host.tld'
    name: '%project-slug%%slug.without-feature%_web_1'
```

And the output of `fab blueprint:feature/XY-123-my_Branch-name,configNamy=<config-name>,output=true` is

```yaml
hosts:
  phbackend-xy-123-my-branch-name.some.host.tld:
    branch: feature/XY-123-my_Branch-name
    configName: phbackend-xy-123-my-branch-name.some.host.tld
    database:
      name: xy123mybranchname_mysql
    docker:
      name: phbackendxy123mybranchname_web_1
      projectFolder: phbackend--xy-123-my-branch-name
      vhost: phbackend-xy123mybranchname.some.host.tld
    inheritsFrom: http://some.host/data.yaml
```


## doctor

The `doctor`-task will try to establish all needed ssh-connections and tunnels and give feedback if anything fails. This should be the task you run if you have any problems connecting to a remote instance.

```shell
fab config:<your-config> doctor
fab config:<your-config> doctor:remote=<your-remote-config>
```
Running the doctor-task without an argument, will test the connectivity to the configuration `<your-cofig>`. If you provide a remote configuration with `:remote=<your-remote-config>` the doctor command will create and test any necessary tunnels to test the connections betwenn `<your-config>` and `<your-remote-config>`. Might be handy if the task `copyFrom` fails.


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
* `platform` will push the current branch to the `platform` remote, which will start the deployment-process on platform.sh

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
  * enable the deployment-module
  * enable modules listed in file `modules_enabled.txt`
  * disable modules listed in file `modules_disabled.txt`
  * revert features (drupal 7) / import the configuration `staging` (drupal 8),
  * run update-hooks
  * enable a deployment-module if any stated in the fabfile.yaml
  * and does a cache-clear.
  * if your host-type is `dev` and `withPasswordReset` is not false, the password gets reset to admin/admin


**Configuration:**

* your host-configuration needs a `branch`-key stating the branch to deploy.
* your configuration needs a `uuid`-entry, this is the site uuid (drupal 8). You can get the site-uuid via `drush cget system.site`
* you can customize which configuration to import with the `configurationManagement`-setting inside your host- or global-setting.

**Examples:**

* `fab config:mbb reset:withPasswordReset=0` will reset the installation and will not reset the password.

## install

```shell
fab config:<your-config> install
fab config:<your-config> install,distribution=thunder
fab config:<your-config> install,locale=de
```

This task will install a new Drupal installation with the minimal-distribution. You can install different distributions, see the examples.

**Available methods:**

*  `drush7` and `drush8`

**Configuration:**

As an alternative you can add a `installOptions`-section to your fabfile.yaml. Here's an example:

```yaml
installOptions:
  distribution: thunder
  locale: es
```

Options via command line will override the settings in your fabfile.yaml.



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

This command will run custom scripts on a remote machine. You can declare scripts globally or per host. If the `script-name` can't be found in the fabfile.yaml you'll get a list of all available scripts.

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
