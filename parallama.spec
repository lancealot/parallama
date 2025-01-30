Name:           parallama
Version:        0.1.0
Release:        1%{?dist}
Summary:        Multi-user authentication and access management service for Ollama

License:        MIT
URL:            https://github.com/yourusername/parallama
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3-devel >= 3.9
BuildRequires:  python3-setuptools
BuildRequires:  postgresql-devel >= 13
Requires:       python3 >= 3.9
Requires:       postgresql-server >= 13
Requires:       redis
Requires:       ollama

%description
Parallama provides a secure API gateway that enables multiple users to access
Ollama services over a network with individual API keys, rate limiting, and
usage tracking.

%prep
%autosetup

%build
%py3_build

%install
%py3_install

# Create directories
mkdir -p %{buildroot}%{_sysconfdir}/parallama
mkdir -p %{buildroot}%{_localstatedir}/log/parallama

# Install systemd service
mkdir -p %{buildroot}%{_unitdir}
install -p -m 644 systemd/parallama.service %{buildroot}%{_unitdir}/

# Install config
install -p -m 644 config/config.yaml %{buildroot}%{_sysconfdir}/parallama/

%files
%license LICENSE
%doc README.md USAGE.md
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}-%{version}*
%{_bindir}/parallama-cli
%{_unitdir}/parallama.service
%dir %{_sysconfdir}/parallama
%config(noreplace) %{_sysconfdir}/parallama/config.yaml
%dir %{_localstatedir}/log/parallama

%post
%systemd_post parallama.service

%preun
%systemd_preun parallama.service

%postun
%systemd_postun_with_restart parallama.service

%changelog
* Mon Jan 29 2025 Your Name <your.email@example.com> - 0.1.0-1
- Initial package
