from yum.plugins import PluginYumExit, TYPE_CORE, TYPE_INTERACTIVE
from yum.packages import YumInstalledPackage
from yum.constants import *
from rpmUtils.miscutils import compareEVR

import sys
import os
import re
sys.path.insert(0,'/usr/share/yum-cli/')

import yum
from yum.Errors import *

from utils import YumUtilBase
from yum import _

import logging
import rpmUtils

requires_api_version = '2.3'
plugin_type = (TYPE_CORE)

KERNEL_PKG_NAME = 'kernel'
MODULE_PKG_BASENAME = 'kmod-nvidia'
MODULE_PKG_PATTERN  = re.compile(MODULE_PKG_BASENAME + '-(branch-[0-9][0-9][0-9]|latest)$')

DRIVER_PKG_BASENAME = 'nvidia-driver'
DRIVER_PKG_PATTERN  = re.compile(DRIVER_PKG_BASENAME + '-(branch-[0-9][0-9][0-9]|latest)$')
DEPEND_ON_KMOD_PATTERNS = [DRIVER_PKG_PATTERN]

def msg(conduit, message):
	conduit.info(1, 'NVIDIA: ' + message + str(conduit) + str(type(conduit)))

def init_hook(conduit):
	"""This is just here to make sure the plugin was loaded correctly.
	   Eventually this should just go away."""
	# conduit.info(2, '#### NVIDIA ####')

def addErase(conduit, tsInfo, package):
	"""additional sanity check that we only try to addErase() installed packages,
	   i.e. RPMInstalledPackage instances. If we add others here, e.g. just
	   YumAvailablePackages, the transaction fails later with a cryptic error message"""
	if isinstance(package, YumInstalledPackage):
		tsInfo.addErase(package)
	else:
		conduit.error(2, 'NVIDIA: tried erasing non-installed package ' + str(package) + '/' + str(type(package)))
		raise AttributeError

def get_module_package(conduit, driverPackage, kernelPackage):
	"""Return the corresponding kernel module package, given an installed driver package
	   and a kernel package."""

	modName = get_module_pkg_name(driverPackage)
	modRelease = get_module_pkg_release(kernelPackage, driverPackage)

	# We search the DB first so we can be sure to get a YumInstalledPackage
	# instance in case the module package is already installed and a
	# YumAvailablePackage instance in case it ins't.
	db = conduit.getRpmDB()
	pkgs = db.searchNevra(modName, driverPackage.epoch, kernelPackage.version, \
		modRelease, driverPackage.arch)

	if pkgs:
		# Assume len(pkgs) == 1, but don't assert
		return pkgs[0]

	try:
		return conduit._base.getPackageObject((modName, driverPackage.arch,
		                                       driverPackage.epoch, kernelPackage.version,
		                                       modRelease))
	except:
		# Do nothing and let the later raise + return handle this case.
		pass

	raise DepError('Could not find suitable Nvidia kernel module version for kernel ' +
		       str(kernelPackage) + ' and driver ' + str(driverPackage))

	return None

def install_modules_for_kernels(conduit, driverPackage, kernelPackages):
	"""Install kernel module packages for all given kernel packages"""
	tsInfo = conduit.getTsInfo()
	db = conduit.getRpmDB()

	newestKernel = get_most_recent_kernel(conduit, kernelPackages)
	modPo = get_module_package(conduit, driverPackage, newestKernel)

	if modPo is None:
		modName = get_module_pkg_name(driverPackage)
		msg(conduit, 'No kernel module package ' + modName + ' for ' + \
			str(newestKernel) + ' and ' + str(driverPackage) + ' found')
		return

	if db.contains(po = modPo):
		return

	tsInfo.addTrueInstall(modPo)

def installing_kernels(conduit, kernelPackages, driverPackage):
	"""When installing new kernels, we need to also install the driver module packages
	for each of them."""
	tsInfo = conduit.getTsInfo()
	db = conduit.getRpmDB()

	# Remove the kernel module package for all other kernels
	newestKernel = get_most_recent_kernel(conduit, kernelPackages)
	allKernels = list(kernelPackages)
	allKernels.extend(db.returnPackages(patterns=[KERNEL_PKG_NAME]))

	for k in allKernels:
		if k != newestKernel:
			modPo = get_module_package(conduit, driverPackage, k)

			if db.contains(po = modPo):
			    addErase(conduit, tsInfo, modPo)

	# Will install the kernel module package for the newest one of the kernel packages
	install_modules_for_kernels(conduit, driverPackage, kernelPackages)

def erasing_kernels(conduit, kernelPackages, driverPackage):
	"""When erasing kernel modules, we want to remove their driver kernel module
	   packages, provided they are installed at all."""
	db = conduit.getRpmDB()
	tsInfo = conduit.getTsInfo()
	currentlyInstalledKernels = db.searchNames([KERNEL_PKG_NAME])

	# This is the list of kernels we will have installed after the given ones were removed.
	remainingKernels = list(set(currentlyInstalledKernels) - set(kernelPackages))

	assert(len(remainingKernels) > 0)
	newestRemainingKernel = sorted(remainingKernels, cmp = compare_po, reverse = True)[0]
	newestModPo = get_module_package(conduit, driverPackage, newestRemainingKernel)

	# Remove kernel module packages for all the kernels we remove
	for k in kernelPackages:
		modPo = get_module_package(conduit, driverPackage, k)

		if newestModPo != modPo and db.contains(po = modPo):
			addErase(conduit, tsInfo, modPo)

	# Install the kernel module package for the now most recent kernel
	if not db.contains(po = newestModPo):
		tsInfo.addTrueInstall(newestModPo)

def erasing_driver(conduit, driverPackage):
	"""When removing the driver package, we automatically remove all the installed
	   kernel module packages."""
	db = conduit.getRpmDB()
	tsInfo = conduit.getTsInfo()
	modPackages = db.returnPackages(patterns=[MODULE_PKG_BASENAME + '*'])

	for modPo in modPackages:
		addErase(conduit, tsInfo, modPo)

def installing_driver(conduit, driverPackage, installingKernels):
	"""We call this when installing the DRIVER_PKG_BASENAME package. If that happens,
	   we need to install kernel module packages for all the installed kernels,
	   as well as the kernels we additionally install in the current transaction"""
	db = conduit.getRpmDB()
	tsInfo = conduit.getTsInfo()

	install_modules_for_kernels(conduit, driverPackage, [])

def postresolve_hook(conduit):
	db = conduit.getRpmDB()
	tsInfo = conduit.getTsInfo()
	erasePkgs = tsInfo.getMembersWithState(output_states=[TS_ERASE, TS_UPDATED])
	installPkgs = tsInfo.getMembersWithState(output_states=[TS_INSTALL, TS_TRUEINSTALL,
	                                                        TS_UPDATE])

	# Append a '*' to all the package names in our list
	installedDriverPackage = db.returnPackages(patterns=[DRIVER_PKG_BASENAME + '*'])

	# The above query for the rpm database returns all packages starting with
	# the DRIVER_PKG_BASENAME, but all the subpackages of the nvidia-driver
	# package start with 'nvidia-driver', so filter the list out for the correct
	# package names.
	for k in list(installedDriverPackage):
		if not is_driver_po(k):
			installedDriverPackage.remove(k)

	installingDriverPackage = None
	erasingDriverPackage = None
	installingKernels = []
	erasingKernels = []

	for pkg in installPkgs:
		if match_list(DEPEND_ON_KMOD_PATTERNS, pkg.name):
			installingDriverPackage = pkg.po
			break

	for pkg in erasePkgs:
		if match_list(DEPEND_ON_KMOD_PATTERNS, pkg.name):
			erasingDriverPackage = pkg.po
			break

	for pkg in erasePkgs:
		if pkg.po.name == KERNEL_PKG_NAME:
			erasingKernels.append(pkg.po)

	for pkg in installPkgs:
		if pkg.po.name == KERNEL_PKG_NAME:
			installingKernels.append(pkg.po)

	# Since this is a postresolve hook, yum might've already added a kernel module
	# package, to satisfy the dependency the nvidia-driver package has. However,
	# we will handle that ourselves so remove all of them here.
	for member in tsInfo.getMembers():
		if MODULE_PKG_PATTERN.match(member.name):
			tsInfo.deselect(member.name)

	if installingDriverPackage:
		installing_driver(conduit, installingDriverPackage, list(installingKernels))

	if erasingDriverPackage:
		erasing_driver(conduit, erasingDriverPackage)

	if installedDriverPackage:
		if installingKernels and not installingDriverPackage:
			installing_kernels(conduit, installingKernels, installedDriverPackage[0])

		if erasingKernels:
			erasing_kernels(conduit, erasingKernels, installedDriverPackage[0])

def preresolve_hook(conduit):
	tsInfo = conduit.getTsInfo()
	moduleUpgrades = filter(lambda m: MODULE_PKG_PATTERN.match(m.name), tsInfo.getMembers())

	# Not interesting for us
	if not moduleUpgrades:
		return

	# Stop yum from automatically updating our packages, since we do it ourselves.
	# This is technically not necessary, but we need to implement all the
	# kmod package update handling ourselves anyway.

	# This should really be the only one
	po = moduleUpgrades[0]
	tsInfo.deselect(po.name)


def match_list(patternList, pkg):
	for p in patternList:
		if p.match(pkg):
			return True;

	return False

def is_driver_po(po):
	return DRIVER_PKG_PATTERN.match(po.name) and 'dkms' not in po.name

def get_module_pkg_name(driverPackage):
	return driverPackage.name.replace(DRIVER_PKG_BASENAME, MODULE_PKG_BASENAME)

def get_module_pkg_release(kernelPackage, driverPackage):
	"""In our scheme, we build up the kmod package release field from the
	   kernel release field as well as the driver version."""
	start = kernelPackage.release[:kernelPackage.release.rfind('.')]
	end = kernelPackage.release[kernelPackage.release.rfind('.'):]

	return start + '.r' + driverPackage.version + end

def compare_po(po1, po2):
	return compareEVR((po1.epoch, po1.version, po1.release),
	                  (po2.epoch, po2.version, po2.release))

def get_most_recent_kernel(conduit, additional=[]):
	db = conduit.getRpmDB()
	kernels = list(additional)
	kernels.extend(db.returnPackages(patterns=[KERNEL_PKG_NAME]))

	return sorted(kernels, cmp = compare_po, reverse = True)[0]
