Name:           parallama
Version:        0.1.0
Release:        1%{?dist}
Summary:        Multi-user authentication and access management service for Ollama

License:        MIT
URL:            https://github.com/yourusername/parallama
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3-devel >= 3.9
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  postgresql-devel >= 13
BuildRequires:  openssl-devel
BuildRequires:  gcc

# Runtime dependencies
Requires:       python3 >= 3.9
Requires:       postgresql-server >= 13
Requires:       redis >= 5.0
Requires:       ollama
# Python package dependencies
Requires:       python3-fastapi >= 0.104.0
Requires:       python3-uvicorn >= 0.24.0
Requires:       python3-pydantic >= 2.4.2
Requires:       python3-sqlalchemy >= 2.0.23
Requires:       python3-psycopg2 >= 2.9.9
Requires:       python3-jose >= 3.3.0
Requires:       python3-passlib >= 1.7.4
Requires:       python3-redis >= 5.0.1
Requires:       python3-httpx >= 0.25.1
Requires:       python3-multipart >= 0.0.6
Requires:       python3-yaml >= 6.0.1
Requires:       python3-click >= 8.1.0
Requires:       python3-tabulate >= 0.9.0
Requires:       python3-typer >= 0.9.0
Requires:       python3-rich >= 13.7.0

%description
Parallama provides a secure API gateway that enables multiple users to access
Ollama services over a network with individual API keys, rate limiting, and
usage tracking.

%prep
%autosetup

%build
%py3_build

%install
# Install Python package
%py3_install

# Remove __pycache__ directories
rm -rf %{buildroot}/%{_bindir}/__pycache__

# Create directories with root:root ownership
mkdir -p %{buildroot}%{_sysconfdir}/parallama
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_localstatedir}/log/parallama
mkdir -p %{buildroot}%{_localstatedir}/lib/parallama

# Install files with root:root ownership
install -p -m 0644 systemd/parallama.service %{buildroot}%{_unitdir}/
install -p -m 0644 config/config.yaml %{buildroot}%{_sysconfdir}/parallama/config.yaml.example

# Create empty secret files
touch %{buildroot}%{_sysconfdir}/parallama/jwt_secret
touch %{buildroot}%{_sysconfdir}/parallama/db_password

%files
%defattr(-,root,root,-)
%license LICENSE
%doc README.md USAGE.md
%{python3_sitelib}/%{name}
%{python3_sitelib}/%{name}-%{version}*
%{_bindir}/parallama-cli
%{_unitdir}/parallama.service

%dir %{_sysconfdir}/parallama
%config(noreplace) %{_sysconfdir}/parallama/config.yaml.example
%config(noreplace) %attr(0640,root,parallama) %{_sysconfdir}/parallama/jwt_secret
%config(noreplace) %attr(0640,root,parallama) %{_sysconfdir}/parallama/db_password

%dir %{_localstatedir}/log/parallama
%dir %attr(0750,parallama,parallama) %{_localstatedir}/lib/parallama

%pre
getent group parallama >/dev/null || groupadd -r parallama
getent passwd parallama >/dev/null || \
    useradd -r -g parallama -s /sbin/nologin -c "Parallama API Gateway" parallama
exit 0

%post
%systemd_post parallama.service

# Set directory ownership and permissions
chown root:parallama %{_sysconfdir}/parallama
chmod 0755 %{_sysconfdir}/parallama
chown parallama:parallama %{_localstatedir}/log/parallama
chmod 0750 %{_localstatedir}/log/parallama
chown parallama:parallama %{_localstatedir}/lib/parallama
chmod 0750 %{_localstatedir}/lib/parallama

# Generate secrets if they don't exist
if [ ! -s %{_sysconfdir}/parallama/jwt_secret ]; then
    openssl rand -hex 32 > %{_sysconfdir}/parallama/jwt_secret
    chown root:parallama %{_sysconfdir}/parallama/jwt_secret
    chmod 0640 %{_sysconfdir}/parallama/jwt_secret
fi

if [ ! -s %{_sysconfdir}/parallama/db_password ]; then
    openssl rand -hex 16 > %{_sysconfdir}/parallama/db_password
    chown root:parallama %{_sysconfdir}/parallama/db_password
    chmod 0640 %{_sysconfdir}/parallama/db_password
fi

%preun
%systemd_preun parallama.service

%postun
%systemd_postun_with_restart parallama.service

%changelog
* Fri Feb 02 2024 Parallama Maintainer <maintainer@parallama.org> - 0.1.0-1
- Initial package
