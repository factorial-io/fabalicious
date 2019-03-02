# Note

Fabalicious is deprecated in favor of [phabalicious](https://github.com/factorial-io/phabalicious) which is available in a stable version now. Fabalicious will only receive important bugfixes.

# How does fabalicious work in two sentences

Fabalicious uses a configuration file with a list of hosts and `ssh` and optionally tools like `composer`, `drush`, `git`, `docker` or custom scripts to run common tasks on remote machines. It is slightly biased to drupal-projects but it works for a lot of other types of projects.

Fabalicious is using [fabric](http://www.fabfile.org) to run tasks on remote machines. The configuration-file contains a list of hosts to work on. Some common tasks are:

 * deploying new code to a remote installation
 * reset a remote installation to its defaults.
 * backup/ restore data
 * copy data from one installation to another
 * optionally work with our docker-based development-stack [multibasebox](https://github.com/factorial-io/multibasebox)

## Documentation

You'll find extensive documentation in the docs-folder or [here](http://factorial-io.github.io/fabalicious/)
