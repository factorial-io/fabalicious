# fabalicious -- huber's deployment scripts

this fabfile is a special crafted deployment script to help deploy drupal installations acrooss different servers.
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
    hosts:
      hostA:
        host: <host>
        port: <port>
        user: <your-ssh-user>
        rootFolder: <absolute-path-to-your-webroot>
        sitesFolder: <relative-path-to-your-sites-folder>
        filesFolder: <relative-path-to-yout-files-folder>
        backupFolder: <absolute-path-where-backup-should-be-stored>
        hasDrush: <boolean>
        useForDevelopment: <boolean>
        reset:
          - "first reset command"
          - "second reset command"
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

* reset: reset the drupal-installation, clear the caches, run update, reset all features, enable deploy-module and its dependencies
* backup: tar all files, dump the database and copy them to the backup-directory
* deploy: update the installation by pulling the newest source from git and running the reset-task afterwards
   
   
   



