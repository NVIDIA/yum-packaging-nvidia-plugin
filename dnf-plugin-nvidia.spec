Name:		dnf-plugin-nvidia
Version:	2.1
Release:	2%{?dist}
Summary:	DNF plugin needed to remove old kernel modules
License:	MIT
BuildArch:	noarch

Source0:	nvidia-dnf.py

BuildRequires: python3-devel

Requires:   python3-dnf

%description
When using precompiled kernel modules, this DNF plugin prevents kernel changes
if there is no matching precompiled kernel module package available.

It also also removes kernel module packages of outdated driver versions from
the system.

%install
install -D -m 644 %{SOURCE0} %{buildroot}%{python3_sitelib}/dnf-plugins/nvidia.py

%files
%{python3_sitelib}/dnf-plugins/*

%changelog
* Thu Jun 13 2024 Simone Caronni <scaronni@nvidia.com> - 2.1-2
- Fix error when running without any driver package installed.
- Print all installed kernels when running standalone, the latest installed
  kernel might not be the running one.

* Wed Jun 05 2024 Simone Caronni <scaronni@nvidia.com> - 2.1-1
- Consider *all* kernel subpackages when locking kernel upgrades.
- The plugin now locks the kernel both in upgrade and downgrade scenarios.
- Print information in nicer format when executing standalone.
- Print all excluded kernel packages and subpackages from the current repository
  information when executing standalone.
- Consider both desktop, headless (compute only) and combined when checking for
  drivers.

* Fri Apr 12 2024 Simone Caronni <scaronni@nvidia.com> - 2.0-2
- Clean up SPEC file, make it build in mock.
- Merge https://github.com/NVIDIA/yum-packaging-nvidia-plugin/pull/9.

* Fri Apr 30 2021 Kevin Mittman <kmittman@nvidia.com> 2.1-1
- Debug mode: avoid index out-of-bounds if no kernel installed (in container)

* Mon Sep 28 2020 Kevin Mittman <kmittman@nvidia.com> 2.0-1
- Handle upgrade scenario when new branch is promoted to latest
- Fix try-catch as per Timm's comments
- Cleanup notice message

* Thu Sep 17 2020 Kevin Mittman <kmittman@nvidia.com> 1.9-1
- Do not block kernel updates if DKMS stream kmod package is installed
- Retrieve k_corepkg hawkey package object rather than string
- Expose plugin as DNF command (for debugging)
- Print verbose output when running as a command

* Wed Sep 9 2020 Kevin Mittman <kmittman@nvidia.com> 1.8-1
- Block kernel-core updates that do not have a matching kmod package

* Tue Sep 8 2020 Kevin Mittman <kmittman@nvidia.com> 1.7-1
- Pass %_python_sitelib as variable to avoid hard-coding python3.6

* Tue Oct 29 2019 Timm Bäder <tbaeder@redhat.com> 1.6-1
- Block kernel updates that do not have a matching kmod package
- Use %python3_sitelib

* Mon Jun 17 2019 Timm Bäder <tbaeder@redhat.com> 1.1-1
- Exclude dkms packages

* Tue May 28 2019 Timm Bäder <tbaeder@redhat.com> 1.0-1
- Initial .spec
