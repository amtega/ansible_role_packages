# Ansible packages role

This is an [Ansible](http://www.ansible.com) role to manage different package set based on distribution name and major release. It supports operating system packages and python packages.

## Role Variables

A list of all the default variables for this role is available in `defaults/main.yml`.

The role setups the following facts:

- `ansible_python_interpreter`: python interpreter in the virtualenv. Only available if the virtualenv is configured,there are python packages and role variable `packages_python_set_ansible_interpreter` is enabled

- `packages_python_virtualenv_dir`: directory (ending with /) containing python virtualenv used by the role. Only available if the virtualenv is configured and there are python packages

- `packages_python_bin_dir`: directory (ending with /) containing the binaries of the virtualenv used by the role. Only available if the virtualenv is configured and there are python packages

- `packages_os_result`: result of the operating system packages setup

- `packages_python_result`: result of the python packages setup

## Example Playbook

This is an example playbook:

```yaml
---

- hosts: all
  roles:
    - role: amtega.packages
      vars:
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

Tests are based on [molecule with docker containers](https://molecule.readthedocs.io/en/latest/installation.html).

```shell
cd amtega.packages

molecule test
```

## License

Copyright (C) 2021 AMTEGA - Xunta de Galicia

This role is free software: you can redistribute it and/or modify it under the terms of:

GNU General Public License version 3, or (at your option) any later version; or the European Union Public License, either Version 1.2 or – as soon they will be approved by the European Commission ­subsequent versions of the EUPL.

This role is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details or European Union Public License for more details.

## Author Information

- Juan Antonio Valiño García.
