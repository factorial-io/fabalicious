#Changelog

## 2.0.x

### new
* `runLocally` for dockerHosts: if set to true for a given dockerHost-configuration, the commands get executed locally.
* `runLocally` for hosts: if set to true for a given host-configuration, all commands are run locally.
* new task `doctor`. This will try to do all necessary connections and will inform of any problems. Good for troubleshooting.
* fabfile.local.yaml will override existing fabfile.yaml-configuration. the file may reside up to three folders above the projects fabfile. See the readme for more info
* support for platform.sh

### changed

* fabfile.yaml.lock is not used anymore. To support offline-mode, fabalicious will store all remote files in the `~/.fabalicious` folder. If loading a remote resource fails, fabalicious will use the local cached version of that file.


## 2.0.0

### new

* you can now specify what features you need. The following features are available: `composer`, `docker`, `drush7`, `drush8`, `git`, `ssh`, `files`, `slack`, `drupalconsole`. You specify your needs in the fabfile with the `needs`-key. You can declare this globally and/or per host.

    ```
    needs:
      - git
      - drush8
      - composer
      - slack
      - ssh
      - files
    ```

    `needs` defaults to `git`, `ssh`, `drush7` and `files` if not set explicitly.

* new key `environment`, you can declare a list of environment-variables in `hosts` and `dockerHosts` which get exposed to the running scripts. You can even use the known replacement-patterns available to scripts

    ```
    environment:
      - ROOT_FOLDER: "%dockerHost.rootFolder%/%host.docker.projectFolder%"
      - TYPE: "%host.type%
    ```


* the replacement-patterns already available for docker-scripts are now available for all scripts.

* every task may have a script, which gets called, when the task gets executed. There are three stages for every task available: `<task>Prepare`, `<task>` and `<task>Finished`. Here's an example for the deploy-task:

    ```
    deployPrepare:
      - echo "Preparing deployment …"
    deploy:
      - echo "Deploying …"
    deployFinished:
      - echo "Finished with deployment."
    ```

* You can now add custom scripts to your fabfile and run it via the `script`-task. Declare your scripts on the root level. Here's an example:

    ```
    scripts:
     testScript:
       - echo "This is a test-script…"
    ```

    Now you can run the script via

    ```
    fab config:<config> script:testScript
    ```

    If you need default arguments, you can split your script-declaration as follows:

    ```
    scripts:
      hello:
        defaults:
          name: world
        script:
          - echo "hello %arguments.name%"
    ```

    Running `fab config:<config> script:hello` will print "hello world". Running `fab config:<config> script:hello,name="universum"` will print "hello universum".


* you can specify a branch when running the deploy-task: `deploy:<branchname>`. This will override the branch temporary.

* You can now specify port and the public port for the startRemoteAccess subtask: To create a tunnel to the mysql-server you can use

    ```
    fab config:<your-config> docker:startRemoteAccess,port=3306,publicPort=33060
    ```
* You can run other tasks from  within your scripts, use the reserved keyword `execute`

    ```
    testScript:
      - execute(deploy)
      - execute(docker, start)
    ```

* It should be easier to extend fabalicious to support other hosting environments or applications. You can now add custom scripts to your fabalicious file and call them when running a specific task. Or you can add a new custom method to the source, which gets called when running a specific task. You can even extend existing methods and register them under a different name. (Needs more documentation.)

* New task `drupalconsole:<command>`. Runs the Drupal Console inside your container, on your host. If `command` is `install` drupal-console gets installed on that environment. The Drupal Console does similar things like drush, but there's currently no support to "deploy" via the drupal console.

### changed

* script-replacements are now prefixed by `host` and `dockerHost`. You’ll get a list of available replacements if fabalicious can’t resolve all replacements successfully.
* All declared yaml-variables are exposed to the script. You can access sub-dictionaries via the dot-syntax, e.g. `host.docker.name`.
* The task `waitForServices` is now part of the docker-method. Invoke it via `docker:waitForServices`
* The task `startRemoteAccess` is now part of the docker-method. Invoke it via `docker:startRemoteAccess`
* The task `copySSHKeyToDocker` is renamed to `copySSHKeys`and is now part of the docker-method. Invoke it via `docker:copySSHKeys`
* the common-section of the fabfile.yaml has changed, you can specify a common script per `type`, e.g.:

    ```
    common:
      dev:
        - echo "dev"
      stage:
        - echo "stage"
      prod:
        - echo "prod"
    ```

    You can even use custom types, but `prod` is reserved for production-installations.



### unsupported

* `useForDevelopment` is unsupported, use `type` with value `dev` or `stage`
* `hasDrush` is unsupported, set your `needs` accordingly.
* `needsComposer` is unsupported, set your `needs` accordingly.
* the custom script-command `run_task` is not supported anymore. Use `execute(<task-name>)` instead.
* the task `updateDrupalCore` is not ported over, not sure if it comes back.


