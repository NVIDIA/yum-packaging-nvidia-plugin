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

DRIVER_PKG_NAME = 'nvidia-driver'
KERNEL_PKG_NAME = 'kernel'
KERNEL_PKG_REAL = 'kernel-core'
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


class NvidiaPlugin(dnf.Plugin):
    name = 'nvidia'

    def __init__(self, base, cli):
        super(NvidiaPlugin, self).__init__(base, cli)
        self.base = base
        self.cli = cli

    def sack(self):
        sack = self.base.sack

        installed_drivers = sack.query().installed().filter(name = DRIVER_PKG_NAME)
        installed_kernel = list(sack.query().installed().filter(name = KERNEL_PKG_NAME))

        if not installed_drivers:
            return

        if not installed_kernel: # container/chroot
            return

        # The most recent installed kernel package
        installed_kernel  = sorted(installed_kernel, reverse = True, key = lambda p: evr_key(p, sack))[0]
        available_kernels = sack.query().available().filter(name = KERNEL_PKG_NAME)
        driver = installed_drivers[0]

        # Exclude all available kernels which are newer than the most recent installed
        # kernel AND do NOT have a kmod package
        for kernelpkg in available_kernels:
            if ver_cmp_pkgs(sack, kernelpkg, installed_kernel) != 1:
                continue

            k_corepkg = str(kernelpkg).replace(KERNEL_PKG_NAME + "-", KERNEL_PKG_REAL + "-")

            kmod_pkg_name = KMOD_PKG_PREFIX + '-' + str(driver.version) + '-' + \
                    str(kernelpkg.version) + '-' + str(remove_release_dist(kernelpkg.release))

            kmod_pkg = sack.query().available().filter(name = kmod_pkg_name, version = driver.version)
            if not kmod_pkg:
                # Exclude kernel
                sack.add_excludes([kernelpkg])
                sack.add_excludes([k_corepkg])
                print('NOTE: Skipping kernel installation since no NVIDIA driver kernel module package ' + \
                    str(kmod_pkg_name) + ' for kernel ' + str(kernelpkg) + ' and driver ' + \
                    str(driver) + ' could be found')

    def resolved(self):
        transaction = self.base.transaction
        # XXX This is a workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1658517
        sack = dnf.sack._rpmdb_sack(self.base)

        for pkg in transaction.remove_set:
            if pkg.name == DRIVER_PKG_NAME:
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
