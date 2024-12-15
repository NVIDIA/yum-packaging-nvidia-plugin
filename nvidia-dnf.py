from __future__ import absolute_import
from __future__ import unicode_literals

import os
import shutil
from functools import cmp_to_key

from dnf.cli.option_parser import OptionParser
import dnf
import dnf.cli
import dnf.sack
import libdnf.transaction

DESKTOP_PKG_NAME = 'nvidia-driver'
COMPUTE_PKG_NAME = 'nvidia-driver-cuda'
KERNEL_PKG_NAME = 'kernel-core'
KMOD_PKG_PREFIX = 'kmod-nvidia'

def is_kmod_pkg(pkg):
    return pkg.name.startswith(KMOD_PKG_PREFIX) and 'dkms' not in pkg.name

def remove_release_dist(release):
    return release[0:release.rfind('.')]

def evr_key(po, sack):
    func = cmp_to_key(sack.evr_cmp)
    return func(str(po.epoch) + ':' + str(po.version) + '-' + str(po.release))

def ver_cmp_pkgs(sack, po1, po2):
    return sack.evr_cmp(str(po1.epoch) + ':' + str(po1.version) + '-' + str(po1.release),
                        str(po2.epoch) + ':' + str(po2.version) + '-' + str(po2.release));

def revive_msg(var, msg, val = ''):
    if var is not None:
        print(msg)

    return val


class NvidiaPlugin(dnf.Plugin):
    name = 'nvidia'

    def __init__(self, base, cli):
        super(NvidiaPlugin, self).__init__(base, cli)
        self.base = base
        self.cli = cli

    def sack(self, debug = None):
        # run as command
        if debug == True:
            base = self.base()
            base.read_all_repos()
            base.fill_sack()
            sack = base.sack
        # run as plugin
        else:
            sack = self.base.sack

        # check installed
        installed_drivers = sack.query().installed().filter(name = [DESKTOP_PKG_NAME, COMPUTE_PKG_NAME])
        installed_kernel = list(sack.query().installed().filter(name = KERNEL_PKG_NAME))
        installed_modules = list(sack.query().installed().filter(name__substr = KMOD_PKG_PREFIX))

        # driver not installed
        if not installed_drivers and debug is None:
            return

        # container/chroot
        if not installed_kernel and debug is None:
            return

        # The most recent installed kernel package
        installed_kernels = sorted(installed_kernel, reverse = True, key = lambda p: evr_key(p, sack))
        if len(installed_kernels) > 0:
            installed_kernel  = installed_kernels[0]

        available_kernels = sack.query().available().filter(name = KERNEL_PKG_NAME)
        available_drivers = sack.query().available().filter(name = [DESKTOP_PKG_NAME, COMPUTE_PKG_NAME])
        dkms_kmod_modules = sack.query().available().filter(name__substr = "dkms")
        available_modules = sack.query().available().filter(name__substr = KMOD_PKG_PREFIX).difference(dkms_kmod_modules)

        # Print debugging if running from CLI
        if installed_kernels:
            string_kernels = '\n  '.join([str(elem) for elem in installed_kernels])
            revive_msg(debug, '\nInstalled kernel(s):\n  ' + str(string_kernels))

        if installed_modules:
            string_modules = '\n  '.join([str(elem) for elem in installed_modules])
            revive_msg(debug, '\nInstalled kmod(s):\n  ' + str(string_modules))

        if available_kernels:
            string_kernels = '\n  '.join([str(elem) for elem in available_kernels])
            revive_msg(debug, '\nAvailable kernel(s):\n  ' + str(string_kernels))

        if available_drivers:
            string_drivers = '\n  '.join([str(elem) for elem in available_drivers])
            revive_msg(debug, '\nAvailable driver(s):\n  ' + str(string_drivers))

        if available_modules:
            string_all_modules = '\n  '.join([str(elem) for elem in available_modules])
            revive_msg(debug, '\nAvailable kmod(s):\n  ' + str(string_all_modules))

        revive_msg(debug, '')

        # DKMS stream enabled
        if installed_modules and 'dkms' in string_modules:
            return

        # Installed driver
        try:
            driver = installed_drivers[0]
        except:
            return

        # Exclude all available kernels which do not have a kmod package
        for kernelpkg in available_kernels:

            # Iterate through drivers in stream
            kmod_pkg = None
            for a_driver in available_drivers:
                # Get package name
                kmod_pkg_name = KMOD_PKG_PREFIX + '-' + str(a_driver.version) + '-' + str(kernelpkg.version) + '-' + str(remove_release_dist(kernelpkg.release))

                # Append object
                if kmod_pkg is not None:
                    kmod_pkg = sack.query().available().filter(name = kmod_pkg_name, version = a_driver.version).union(kmod_pkg)
                else:
                    kmod_pkg = sack.query().available().filter(name = kmod_pkg_name, version = a_driver.version)

            # kmod for kernel and driver combination not available
            if not kmod_pkg:

                # Assemble a list of all packages that are built from the same kernel source rpm
                all_rpms_of_kernel = sack.query().available().filter(release = kernelpkg.release)

                string_all_rpms_of_kernel = '\n  '.join([str(elem) for elem in all_rpms_of_kernel])
                revive_msg(debug, 'Excluded kernel packages during update (' + str(kernelpkg.version) + '-' + str(kernelpkg.release) + '):\n  ' + str(string_all_rpms_of_kernel))
                revive_msg(debug, '')

                # Exclude packages
                if debug is None:
                    try:
                        sack.add_excludes(all_rpms_of_kernel)
                        print('NVIDIA driver: filtering kernel ' + str(kernelpkg.version) + '-' + str(kernelpkg.release) + ', no precompiled modules available for version ' + str(driver.epoch) + ':' + str(driver.version))
                    except Exception as error:
                        print('WARNING: kernel exclude error', error)

    def resolved(self):
        transaction = self.base.transaction

        for pkg in transaction.remove_set:
            if pkg.name == DESKTOP_PKG_NAME or pkg.name == COMPUTE_PKG_NAME:
                # We are removing a driver package, through an
                # actual remove or an upgrade. Remove all
                # kmod packages belonging to it as well.
                installed_kmods = sack.query().installed().filter(version = pkg.version)

                # The above query only selects by version since we don't know
                # the exact name of the kmod package. Look here for them by prefix
                # and remove them if they match the version of the driver
                # we're removing right now.
                for kmod in installed_kmods:
                    if is_kmod_pkg(kmod):
                        transaction.add_erase(kmod)


@dnf.plugin.register_command
class NvidiaPluginCommand(dnf.cli.Command):
    aliases = ('nvidia-plugin',)
    summary = 'Helper plugin for DNF to manage precompiled NVIDIA driver streams'

    def run(self):
        nvPlugin = NvidiaPlugin(dnf.Base, dnf.cli.Cli)
        nvPlugin.sack(True)
