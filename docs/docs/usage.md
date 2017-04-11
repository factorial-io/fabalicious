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
* platform

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