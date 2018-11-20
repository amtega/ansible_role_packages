# Ansible packages role

This is an [Ansible](http://www.ansible.com) role to manage different package set based on distribution name and major release. It supports operating system packages and python packages.

## Requirements

[Ansible 2.7+](http://docs.ansible.com/ansible/latest/intro_installation.html)

## Role Variables

A list of all the default variables for this role is available in `defaults/main.yml`.

## Modules

The role provides these modules:

- packages_shadow_facts: get remote encrypted shadow password information for a set of users.

## Dependencies

- [amtega.check_platform](https://galaxy.ansible.com/amtega/check_platform)
- [amtega.proxy_client](https://galaxy.ansible.com/amtega/proxy_client). If you need a proxy for internet access fill this role variables.
- [amtega.epel](https://galaxy.ansible.com/amtega/epel). If distribution is CentOS or RHEL.

## Example Playbook

This is an example playbook:

```yaml
---

- hosts: all
  roles:
    - role: amtega.packages
      packages_os:
        all:
          all:
            lynx: present
        centos:
          all:
            telnet: present
          6:
            httpd: present
          7:
            - name: "{{ package_name }}"
              state: present
            - tomcat: present
        fedora:
          27:
            httpd: present
            tomcat: present
          28:
            httpd: present
            tomcat: present
      packages_python:
        debian:
          9:
            "pexpect>=3.3": present
        centos:
          6:
            - "pexpect>=3.3": present
            - "gitlab": present
          7:
            "pexpect>=3.3": present
        fedora:
          27:
            "pexpect>=3.3": present
          28:
            "pexpect>=3.3": present
  vars:
    package_name: "httpd"
```

## Testing

Tests are based on docker containers. You can setup docker engine quickly using the playbook `files/setup.yml` available in the role [amtega.docker_engine](https://galaxy.ansible.com/amtega/docker_engine).

Once you have docker, you can run the tests with the following commands:

```shell
$ cd amtega.packages/tests
$ ansible-playbook main.yml
```

## License

Copyright (C) 2018 AMTEGA - Xunta de Galicia

This role is free software: you can redistribute it and/or modify it under the terms of:

GNU General Public License version 3, or (at your option) any later version; or the European Union Public License, either Version 1.2 or – as soon they will be approved by the European Commission ­subsequent versions of the EUPL.

This role is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details or European Union Public License for more details.

## Author Information

- Juan Antonio Valiño García.
