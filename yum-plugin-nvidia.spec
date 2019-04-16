Name:		yum-plugin-nvidia
Version:	0.2
Release:	1%{?dist}
Summary:	YUM plugin to handle Nvidia driver module packages

Group:		System/Kernel
License:	GPLv2+
URL:		http://git.engineering.redhat.com/git/users/tbaeder/yum-plugin-nvidia.git/
BuildArch:	noarch
Source0:	nvidia-yum.py
Source1:	nvidia.conf

Requires:	python

%description
The nvidia yum plugin helps keeping the necessary nvidia kernel module
packages installed at all times.


%build
# Empty

%prep
# Empty

%install
mkdir -p %{buildroot}%{_sysconfdir}/yum/
mkdir -p %{buildroot}%{_sysconfdir}/yum/pluginconf.d/
install -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/yum/pluginconf.d/

mkdir -p %{buildroot}%{_prefix}/lib/yum-plugins/
install -m 644 %{SOURCE0} %{buildroot}%{_prefix}/lib/yum-plugins/nvidia.py

%files
%{_prefix}/lib/yum-plugins/nvidia.py*
%config(noreplace) %{_sysconfdir}/yum/pluginconf.d/nvidia.conf

%changelog
* Tue Apr 16 2019 Timm Bäder <tbaeder@redhat.com> 0.2-1
 - Stop yum from automatically updating kmod packages

* Thu Jun 21 2018 Timm Bäder <tbaeder@redhat.com> 0.1-1
 - Initial revision
