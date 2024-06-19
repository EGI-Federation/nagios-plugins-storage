# Package needs to stay arch specific (due to nagios plugins location), but
# there's nothing to extract debuginfo from
%global debug_package %{nil}

%define nagios_plugins_dir %{_libdir}/nagios/plugins

Name:       nagios-plugins-storage
Version:    0.1.2
Release:    1%{?dist}
Summary:    Nagios probes to be run remotely against EGI Online endpoints
License:    MIT
Group:      Applications/Internet
URL:        https://github.com/EGI-Federation/nagios-plugins-storage
# The source of this package was pulled from upstream's vcs. Use the
# following commands to generate the tarball:
Source0:   %{name}-%{version}.tar.gz
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

Requires:   nagios%{?_isa}
Requires:   python3
Requires:   gfal2-python3
Requires:   python3-nap
Requires:   gfal2-plugin-file
Requires:   gfal2-plugin-xrootd
Requires:   gfal2-plugin-http 

%description
This package provides the nagios probes for XRootD

%prep
%setup -q -n %{name}-%{version}

%build

%install
make install DESTDIR=%{buildroot}
mkdir -p %{buildroot}%{_libdir}/nagios/plugins/storage
cp --preserve=timestamps plugins/*.py %{buildroot}%{_libdir}/nagios/plugins/storage

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{nagios_plugins_dir}/storage
%doc LICENSE README.md

%changelog
* Wed Jun 19 2024 Andrea Manzi <andrea.manzi@egi.eu> - 0.1.2-1
- Add support for bearer tokens

* Tue Jun 18 2024 Andrea Manzi <andrea.manzi@egi.eu> - 0.1.1-1
- Add read-only option

* Mon Jun 17 2024 Andrea Manzi <andrea.manzi@egi.eu> - 0.1.0-0
- EL9 version

* Wed Nov 16 2022 Andrea Manzi <andrea.manzi@egi.eu> - 0.0.1-0
- first version
