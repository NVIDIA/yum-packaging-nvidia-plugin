%define pythonX_sitelib	%{?_python_sitelib}%{?!_python_sitelib:/usr/lib/python3.6/site-packages}
Name:		dnf-plugin-nvidia
Version:	1.7
Release:	1%{?dist}
Summary:	DNF plugin needed to remove old kernel modules

License:	MIT
Source0:	nvidia-dnf.py

BuildArch:	noarch
BuildRequires:	python3

%description
This DNF plugin removes kernel module packages of outdated driver versions
from the system and prevent kernel updates


%install
mkdir -p %{buildroot}/usr/lib/
mkdir -p %{buildroot}%{pythonX_sitelib}/
mkdir -p %{buildroot}%{pythonX_sitelib}/dnf-plugins/

install -m 644 %{SOURCE0} %{buildroot}%{pythonX_sitelib}/dnf-plugins/nvidia.py

%files
%{pythonX_sitelib}/dnf-plugins/nvidia.*
%{pythonX_sitelib}/dnf-plugins/__pycache__/nvidia.*

%changelog
* Tue Sep 8 2020 Kevin Mittman <kmittman@nvidia.com> 1.7-1
 - Pass %_python_sitelib as variable to avoid hard-coding python3.6

* Tue Oct 29 2019 Timm Bäder <tbaeder@redhat.com> 1.6-1
 - Block kernel updates that do not have a matching kmod package
 - Use %python3_sitelib. 

* Mon Jun 17 2019 Timm Bäder <tbaeder@redhat.com> 1.1-1
 - Exclude dkms packages

* Tue May 28 2019 Timm Bäder <tbaeder@redhat.com> 1.0-1
 - Initial .spec
