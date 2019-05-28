Name:		dnf-plugin-nvidia
Version:	1.0
Release:	1%{?dist}
Summary:	DNF plugin needed to remove old kernel modules

License:	MIT
Source0:	nvidia-dnf.py

BuildArch:	noarch
BuildRequires:	python3

%description
This DNF plugin removes kernel module packages of outdated driver versions
from the system


%install
# TODO: Don't hardcode the {python3_sitelib} value?!
mkdir -p %{buildroot}/usr/lib/
mkdir -p %{buildroot}/usr/lib/python3.6/
mkdir -p %{buildroot}/usr/lib/python3.6/site-packages/
mkdir -p %{buildroot}/usr/lib/python3.6/site-packages/dnf-plugins/

install -m 644 %{SOURCE0} %{buildroot}/usr/lib/python3.6/site-packages/dnf-plugins/nvidia.py

%files
#%{python3_sitelib}/dnf-plugins/nvidia.*
/usr/lib/python3.6/site-packages/dnf-plugins/nvidia.*
/usr/lib/python3.6/site-packages/dnf-plugins/__pycache__/nvidia.*
#%{python3_sitelib}/dnf-plugins/__pycache__/nvidia.*

%changelog
* Tue May 28 2019 Timm Bäder <tbaeder@redhat.com> 1.0-1
 - Initial .spec
