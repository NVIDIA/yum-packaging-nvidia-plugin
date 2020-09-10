# yum packaging nvidia plugin

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Contributing](https://img.shields.io/badge/Contributing-Developer%20Certificate%20of%20Origin-violet)](https://developercertificate.org)

## Overview

Packaging templates for `yum` and `dnf` based Linux distros for Python plugin to manage NVIDIA driver precompiled kernel module packages.

The `main` branch contains this README and a sample build script. The `.spec` and `nvidia.py` files can be found in the appropriate [rhel7](../../tree/rhel7), [rhel8](../../tree/rhel8), and [fedora](../../tree/fedora) branches.

## Table of Contents

- [Overview](#Overview)
- [Deliverables](#Deliverables)
- [Prerequisites](#Prerequisites)
  * [Clone this git repository](#Clone-this-git-repository)
  * [Install build dependencies](#Install-build-dependencies)
- [Demo](#Demo)
- [Building with script](#Building-with-script)
  * [Fetch script from main branch](#Fetch-script-from-main-branch)
  * [Usage](#Usage)
- [Building Manually](#Building-Manually)
  * [Packaging plugin](#Packaging-plugin)
  * [Sign RPM packages with GPG signing key](#Sign-RPM-packages-with-GPG-signing-key)
- [Other NVIDIA driver packages](#Other-NVIDIA-driver-packages)
  * [Precompiled kernel modules](#Precompiled-kernel-modules)
- [Contributing](#Contributing)


## Deliverables

This repo contains the `.spec` file used to build the following **RPM** packages:

* **RHEL8** or **Fedora**
  ```shell
  dnf-plugin-nvidia-${version}-${rel}.${dist}.noarch.rpm
  > ex: dnf-plugin-nvidia-1.6-1.el8.noarch.rpm
  ```

* **RHEL7**
  ```shell
  yum-plugin-nvidia-${version}-${rel}.${dist}.noarch.rpm
  > ex: yum-plugin-nvidia-0.5-1.el7.noarch.rpm
  ```

## Prerequisites

### Clone this git repository:

Supported branches: `rhel7`, `rhel8` & `fedora`

```shell
git clone -b ${branch} https://github.com/NVIDIA/yum-packaging-nvidia-plugin
> ex: git clone -b rhel8 https://github.com/NVIDIA/yum-packaging-nvidia-plugin
```

### Install build dependencies
> *note:* these are only needed for building not installation

```shell
# Python
yum install python36

# Packaging
yum install rpm-build
```


## Demo

![Demo](https://developer.download.nvidia.com/compute/github-demos/yum-packaging-nvidia-plugin/demo.gif)

[![asciinema](https://img.shields.io/badge/Play%20Video-asciinema-red)](https://developer.download.nvidia.com/compute/github-demos/yum-packaging-nvidia-plugin/demo-ascii/)


## Building with script

### Fetch script from `main` branch

```shell
cd yum-packaging-nvidia-plugin
git checkout remotes/origin/main -- build.sh
```

### Usage

```shell
./build.sh
```


## Building Manually

### Packaging plugin

#### RHEL8 or Fedora

```shell
mkdir BUILD BUILDROOT RPMS SRPMS SOURCES SPECS
cp nvidia-dnf.py SOURCES/
cp dnf-plugin-nvidia.spec SPECS/

rpmbuild \
    --define "%_topdir $(pwd)" \
    --define "debug_package %{nil}" \
    --define "_python_sitelib $pythonLocation" \
    -v -bb SPECS/dnf-plugin-nvidia.spec

> ex: rpmbuild \
    --define "%_topdir $(pwd)" \
    --define "debug_package %{nil}" \
    --define "_python_sitelib /usr/lib/python3.6/site-packages" \
    -v -bb SPECS/dnf-plugin-nvidia.spec
```

#### RHEL7

```shell
mkdir BUILD BUILDROOT RPMS SRPMS SOURCES SPECS
cp nvidia.conf SOURCES/
cp nvidia-yum.py SOURCES/
cp yum-plugin-nvidia.spec SPECS/

rpmbuild \
    --define "%_topdir $(pwd)" \
    --define "debug_package %{nil}" \
    -v -bb SPECS/yum-plugin-nvidia.spec
```

### Sign RPM package(s) with GPG signing key

If one does not already exist, [generate a GPG key pair](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/packaging_and_distributing_software/advanced-topics)

```shell
gpg --generate-key
```

Set `$gpgKey` to secret key ID.

```shell
gpgArgs="/usr/bin/gpg --force-v3-sigs --digest-algo=sha512 --no-verbose --no-armor --no-secmem-warning"
for package in RPMS/noarch/*-plugin-nvidia*.rpm; do
  rpm \
    --define "%_signature gpg" \
    --define "%_gpg_name $gpgKey" \
    --define "%__gpg /usr/bin/gpg" \
    --define "%_gpg_digest_algo sha512" \
    --define "%_binary_filedigest_algorithm 10" \
    --define "%__gpg_sign_cmd %{__gpg} $gpgArgs -u %{_gpg_name} \
      -sbo %{__signature_filename} %{__plaintext_filename}" \
    --addsign "$package";
done
```


## Other NVIDIA driver packages

### Precompiled kernel modules

* [https://github.com/NVIDIA/yum-packaging-precompiled-kmod](https://github.com/NVIDIA/yum-packaging-precompiled-kmod)

> *note:* more `git` repos with various `.spec` files **coming soon!**


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
