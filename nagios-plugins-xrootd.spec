# Package needs to stay arch specific (due to nagios plugins location), but
# there's nothing to extract debuginfo from
%global debug_package %{nil}

%define nagios_plugins_dir %{_libdir}/nagios/plugins

Name:       nagios-plugins-xrootd
Version:    0.0.1
Release:    1%{?dist}
Summary:    Nagios probes to be run remotely against XRootD endpoints
License:    ASL 2.0
Group:      Applications/Internet
URL:        https://github.com/EGI-Foundation/nagios-plugins-xrootd
# The source of this package was pulled from upstream's vcs. Use the
# following commands to generate the tarball:
Source0:   %{name}-%{version}.tar.gz
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

BuildRequires:  cmake
Requires:   nagios%{?_isa}
Requires:   python%{?_isa}
Requires:   gfal2-python%{?_isa}
Requires:   python-nap
Requires:   gfal2-plugin-file
Requires:   gfal2-plugin-xrootd

%description
This package provides the nagios probes for XRootD

%prep
%setup -q -n %{name}-%{version}

%build
%cmake . -DCMAKE_INSTALL_PREFIX=/

make %{?_smp_mflags}

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}

make install DESTDIR=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{nagios_plugins_dir}/xrootd
%doc LICENSE README.md

%changelog
* Wed Dec 1 2021 Andrea Manzi <andrea.manzi@egi.eu> - 0.0.1-0
- first version
