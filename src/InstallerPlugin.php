<?php

namespace Factorial\Fabalicious;

use Composer\Composer;
use Composer\EventDispatcher\EventSubscriberInterface;
use Composer\IO\IOInterface;
use Composer\Plugin\PluginInterface;
use Composer\Script\Event;
use Composer\Script\ScriptEvents;
use Composer\Util\Filesystem;

/**
 * A Composer plugin to do some custom handling installing fabalicious.
 */
class InstallerPlugin implements PluginInterface, EventSubscriberInterface {

  protected $io;

  /**
   * Construct a new Composer NPM bridge plugin.
   */
  public function __construct() {
  }

  /**
   * Activate the plugin.
   */
  public function activate(Composer $composer, IOInterface $io) {
    $this->io = $io;
  }

  /**
   * Get the event subscriber configuration for this plugin.
   */
  public static function getSubscribedEvents(): array {
    return [
      ScriptEvents::POST_INSTALL_CMD => 'onPostInstallCmd',
    ];
  }

  /**
   * Handle post install command events.
   */
  public function onPostInstallCmd(Event $event) {

    $fs = new Filesystem();

    $working_dir = getcwd();
    $fabalicious_dir = dirname(__DIR__);

    $relative_dir = $fs->findShortestPath($working_dir, $fabalicious_dir);
    $fs->remove('fabfile.py');
    system(sprintf('ln -s %s/fabfile.py fabfile.py', $relative_dir));

    $this->io->write('Created symlink for fabalicious.');
  }

}
