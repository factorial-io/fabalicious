# fabalicious -- huber's deployment scripts

this fabfile is a special crafted deployment script to help deploy drupal installations acrooss different servers.
It reads a yaml-file called "fabfile.yaml" where all hosts are stored.

##Prerequisites

on mac os x:

    brew install python
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
   
   
   



