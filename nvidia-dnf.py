from __future__ import absolute_import
from __future__ import unicode_literals

import os
import shutil

from dnf.cli.option_parser import OptionParser
import dnf
import dnf.cli
import dnf.sack

DRIVER_PKG_NAME = 'nvidia-driver'
KMOD_PKG_PREFIX = 'kmod-nvidia'

class NvidiaPlugin(dnf.Plugin):
    name = 'nvidia'

    def __init__(self, base, cli):
        super(NvidiaPlugin, self).__init__(base, cli)
        self.base = base
        self.cli = cli

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
                    if kmod.name.startswith(KMOD_PKG_PREFIX):
                        transaction.add_erase(kmod)
