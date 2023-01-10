#!/usr/bin/python
# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from shutil import rmtree
from traceback import format_exc
import json
import re
import subprocess
import time


class PackagesManager:
    def __init__(self,
                 ansible_python_interpreter,
                 distribution_name,
                 distribution_version,
                 distribution_aliases,
                 family,
                 packages_os,
                 packages_os_hostvars,
                 packages_os_present,
                 packages_os_managed,
                 packages_capabilities_present,
                 packages_groups_present,
                 packages_python,
                 packages_python_hostvars,
                 packages_python_present,
                 packages_python_managed,
                 python_process_required,
                 python_version,
                 python_virtualenv,
                 python_virtualenv_command,
                 python_virtualenv_python,
                 python_virtualenv_site_packages,
                 python_virtualenv_exists,
                 python_virtualenv_needs_upgrade,
                 python_previous_virtualenv,
                 python_extra_args,
                 timeout,
                 debug):
        self.__ansible_python_interpreter = ansible_python_interpreter
        self.__distribution_name = distribution_name
        self.__distribution_version = distribution_version
        self.__distribution_aliases = distribution_aliases
        self.__family = family
        self.__packages_os = packages_os
        self.__packages_os_hostvars = packages_os_hostvars
        self.__packages_os_present = packages_os_present
        self.__packages_os_managed = packages_os_managed
        self.__packages_capabilities_present = packages_capabilities_present
        self.__packages_groups_present = packages_groups_present
        self.__packages_python = packages_python
        self.__packages_python_hostvars = packages_python_hostvars
        self.__packages_python_present = packages_python_present
        self.__packages_python_managed = packages_python_managed
        self.__python_process_required = python_process_required
        self.__python_virtualenv = python_virtualenv
        self.__python_virtualenv_command = python_virtualenv_command
        self.__python_virtualenv_python = python_virtualenv_python
        self.__python_virtualenv_site_packages = \
            python_virtualenv_site_packages
        self.__python_virtualenv_exists = python_virtualenv_exists
        self.__python_virtualenv_needs_upgrade = \
            python_virtualenv_needs_upgrade
        self.__python_previous_virtualenv = python_previous_virtualenv
        self.__python_extra_args = python_extra_args
        self.__timeout = timeout
        self.__debug = debug

        self.__debug_info = dict()
        self.__changed = False
        self.__packages_present = list()
        self.__packages_managed = list()

        self.__distribution_name_alias = self.__distribution_aliases.get(
            self.__distribution_name,
            self.__distribution_name).lower()

        if self.__distribution_name in ["centos", "redhat"]:
            if int(self.__distribution_version) > 6:
                self.__package_module = "yum"
            else:
                self.__package_module = "legacy"
        else:
            self.__package_module = "dnf"

        if self.__family == "os":
            self.__packages_to_manage = \
                self.__packages_os
            self.__packages_to_manage_hostvars = \
                self.__packages_os_hostvars
            self.__packages_managed = \
                self.__packages_os_managed
        elif self.__family == "python":
            self.__packages_to_manage = \
                self.__packages_python
            self.__packages_to_manage_hostvars = \
                self.__packages_python_hostvars
            self.__packages_managed = \
                self.__packages_python_managed

        if int(self.__distribution_version) >= 7:
            self.__python_os_package = "python3"
            self.__pip_os_package = "python3-pip"
            self.__virtualenv_os_package = "python3-virtualenv"
            self.__setup_tools_os_package = "python3-setuptools"
            self.__rpm_command = "/usr/bin/rpm"
            self.__grep_command = "/usr/bin/grep"
            self.__sort_command = "/usr/bin/sort"
        else:
            self.__python_os_package = None
            self.__pip_os_package = None
            self.__virtualenv_os_package = None
            self.__setup_tools_os_package = None
            self.__rpm_command = "/bin/rpm"
            self.__grep_command = "/bin/grep"
            self.__sort_command = "/bin/sort"

    def _run(self, cmds=[], shell=False, env={}):
        """Run pipelined commands"""
        try:
            subprocess.TimeoutExpired(cmds[0], self.__timeout)
            timeout_supported = True
        except Exception:
            timeout_supported = False

        procs = list()
        start_time = time.time()

        for i, cmd in enumerate(cmds):
            args = dict(
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
                env=env,
                universal_newlines=True)
            if i > 0:
                args["stdin"] = procs[i-1].stdout

            proc = subprocess.Popen(cmd, **args)
            procs.append(proc)

            if proc.returncode not in [0, None]:
                raise Exception("Error running command " + str(cmd))

        proc = procs[-1]

        if not timeout_supported:
            while self.__timeout and proc.poll() is None:
                if time.time()-start_time >= self.__timeout:
                    proc.kill()
                    raise Exception("Timeout running " + cmds[-1])
            stdout = proc.stdout
            stderr = proc.stderr
        else:
            try:
                stdout, stderr = proc.communicate(timeout=self.__timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise Exception("Timeout running " + proc.args)

        if not isinstance(stdout, str):
            stdout = "\n".join(stdout.readlines())

        if not isinstance(stderr, str):
            stderr = "\n".join(stderr.readlines())

        return (stdout, stderr)

    def _gather_os_packages(self):
        """Gather os packages"""
        self.__debug_info["packages_os_gathered"] = False
        if self.__packages_os_present is None:
            self.__debug_info["packages_os_gathered"] = True
            cmd = [self.__rpm_command, "-qa", "--queryformat", "%{NAME}\n"]

            try:
                stdout, stderr = self._run([cmd])
            except Exception:
                raise Exception("Cannot gather installed packages")
            self.__packages_os_present = stdout.splitlines()

        if self.__family == "os":
            self.__packages_present = \
                self.__packages_present + self.__packages_os_present

    def _gather_os_packages_capabilites(self):
        """Gather los packages capabilities"""
        self.__debug_info["capabilites_gathered"] = False
        if self.__packages_capabilities_present is None:
            self.__debug_info["capabilites_gathered"] = True
            cmd1 = [self.__rpm_command, "-qa", "--provides"]
            cmd2 = ["/usr/bin/cut", "-d", "=", "-f", "1"]
            cmd3 = [self.__grep_command, "-v", "("]
            cmd4 = [self.__sort_command]
            cmd5 = ["/usr/bin/uniq"]
            try:
                stdout, stderr = self._run([cmd1, cmd2, cmd3, cmd4, cmd5])
            except Exception:
                raise Exception("Cannot gather installed capabilites")
            self.__packages_capabilities_present = \
                list((p.strip() for p in stdout.splitlines()))

        if self.__family == "os":
            self.__packages_present = \
                self.__packages_present + self.__packages_capabilities_present

    def _gather_os_packages_groups(self):
        """Gather os packages groups"""
        self.__debug_info["groups_gathered"] = False
        if self.__packages_groups_present is None:
            self.__packages_groups_present = list()
            if int(self.__distribution_version) > 6:
                self.__debug_info["groups_gathered"] = True

                # When shell is true is recommended that cmd be a string
                cmd = "/usr/bin/yum group list"
                try:
                    env = {"LANGUAGE": "en_US"}
                    stdout, stderr = self._run([cmd], shell=True, env=env)
                except Exception:
                    raise Exception("Cannot gather installed groups")

                lines = stdout.splitlines()

                regex_installed = re.compile("^Installed")
                regex_available = re.compile("^Available")
                regex_group = re.compile("^   ")

                gather_groups = False
                for line in lines:
                    if regex_installed.match(line):
                        gather_groups = True
                    elif regex_available.match(line):
                        gather_groups = False
                    elif regex_group.match(line) and gather_groups:
                        self.__packages_groups_present.append(
                            "@" + line.strip())

        if self.__family == "os":
            self.__packages_present = \
                self.__packages_present + self.__packages_groups_present

    def _gather_python(self):
        """Gather python"""
        self.__python_interpreter = "{virtualenv_path}/bin/python".format(
            virtualenv_path=self.__python_virtualenv)
        self.__python_bin_dir = \
            "{path}/bin/".format(path=self.__python_virtualenv)

    def _gather_python_packages(self):
        """Gather python packages"""
        self.__debug_info["packages_python_gathered"] = False
        if self.__family == "python" \
           and (self.__packages_python_present is None
                or (self.__python_previous_virtualenv is not None
                    and self.__python_previous_virtualenv
                    != self.__python_virtualenv)):
            if len(self.__python_virtualenv) > 0:
                packages_pip_dir = "{virtualenv}/bin/".format(
                                virtualenv=self.__python_virtualenv)
            else:
                packages_pip_dir = self.__python_bin_dir

            self.__debug_info["packages_python_gathered"] = True
            cmd1 = [packages_pip_dir + "pip", "list"]
            cmd2 = ["/usr/bin/awk", "{ print $1 };"]
            try:
                stdout, stderr = self._run([cmd1, cmd2])
            except Exception:
                raise Exception("Cannot gather installed python packages")

            self.__packages_python_present = \
                list((p.strip() for p in stdout.splitlines()[2:]))

        if self.__family == "python":
            self.__packages_present = self.__packages_python_present

    def _gather_virtualenv_status(self):
        """Gather virtualenv status"""
        if self.__family == "python" and not self.__python_virtualenv_exists:
            cmd = [
                self.__python_interpreter,
                "-c",
                "'from sys import version_info ; print(version_info[0])'"
            ]
            try:
                stdout, stderr = self._run([cmd])
                if len(stderr) == 0:
                    self.__python_virtualenv_exists = True

                if len(stdout) > 0 and int(stdout) < 3:
                    self.__python_virtualenv_needs_upgrade = True
                else:
                    self.__python_virtualenv_needs_upgrade = False
            except Exception:
                self.__python_virtualenv_exists = False

    def _normalize_structure(self, structure):
        """Return a normalized packages structure"""
        normalized_structure = {}
        for distribution in structure:
            for release in structure[distribution]:
                item = structure[distribution][release]
                normalized_items = []
                if isinstance(item, dict):
                    for package in item:
                        normalized_item = {"name": package,
                                           "state": item[package]}
                        normalized_items.append(normalized_item)

                if isinstance(item, list):
                    for subitem in item:
                        if len(subitem.keys()) == 1:
                            normalized_item = {
                                            "name": list(subitem.keys())[0],
                                            "state": list(subitem.values())[0]}
                            normalized_items.append(normalized_item)
                        else:
                            normalized_items.append(subitem)

                if distribution not in normalized_structure.keys():
                    normalized_structure[distribution] = {}

                if release not in normalized_structure[distribution]:
                    normalized_structure[distribution][release] = \
                        normalized_items
                else:
                    normalized_structure[distribution][release] += \
                        normalized_items

        return normalized_structure

    def _combine_structures(self, structures):
        """Combine the list of packags structures into one dict"""
        normalized_structures = []
        for structure in structures:
            normalized_structures.append(self._normalize_structure(structure))

        combined_structures = {}
        for structure in normalized_structures:
            for distribution in structure:
                for release in structure[distribution]:
                    structure_packages = structure[distribution][release]

                    if distribution not in combined_structures.keys():
                        combined_structures[distribution] = {}

                    if release not in combined_structures[distribution].keys():
                        combined_structures[distribution][release] = []

                    combined_structures[distribution][release] += \
                        structure_packages

        return combined_structures

    def _get_python_os_packages_structure(self):
        """Return struture for python os packages"""
        if self.__python_os_package is not None \
           and self.__python_os_package not in self.__packages_os_present:
            self.__python_os_packages = \
                [dict(name=self.__python_os_package,
                      state="present")]
        else:
            self.__python_os_packages = list()

        if self.__pip_os_package is not None \
           and self.__pip_os_package not in self.__packages_os_present:
            self.__python_os_packages = \
                self.__python_os_packages \
                + [dict(name=self.__pip_os_package,
                        state="present")]

        if self.__setup_tools_os_package is not None \
           and self.__setup_tools_os_package \
                not in self.__packages_os_present:
            self.__python_os_packages = \
                self.__python_os_packages \
                + [dict(name=self.__setup_tools_os_package,
                        state="present")]

        if self.__virtualenv_os_package is not None \
           and self.__virtualenv_os_package not in self.__packages_os_present:
            self.__python_os_packages = \
               self.__python_os_packages \
               + [dict(name=self.__virtualenv_os_package,
                       state="present")]

        return dict(all=dict(all=self.__python_os_packages))

    def _get_package_spec(self,
                          name,
                          state,
                          virtualenv=None,
                          virtualenv_command=None,
                          virtualenv_python=None,
                          virtualenv_site_packages=None,
                          extra_args=None):
        """Return package specification"""

        package_managed = next((p for p in self.__packages_managed
                                if p["name"] == name), None)
        package_present = name in self.__packages_present

        result = None
        if (package_managed is None or package_managed["state"] != state) \
           and ((state == "present" and not package_present)
                or (state == "absent" and package_present)
                or state not in ["absent", "present"]):
            result = dict(name=name, state=state)

            if virtualenv is not None and len(virtualenv) > 0:
                result["virtualenv"] = virtualenv

            if virtualenv_command is not None and len(virtualenv_command) > 0:
                result["virtualenv_command"] = virtualenv_command

            if virtualenv_python is not None and len(virtualenv_python) > 0:
                result["virtualenv_python"] = virtualenv_python

            if virtualenv_site_packages is not None:
                result["virtualenv_site_packages"] = virtualenv_site_packages

            if extra_args is not None and len(extra_args) > 0:
                result["extra_args"] = extra_args

            if state == "absent":
                if self.__family == "os" \
                   and name in self.__packages_os_present:
                    self.__packages_os_present.remove(name)
                if self.__family == "python" \
                   and name in self.__packages_python_present:
                    self.__packages_python_present.remove(name)

        return result

    def _get_packages_to_manage(self):
        """Get packages to manage"""
        packages_spec = self._combine_structures(
                            [json.loads(json.dumps(self.__packages_to_manage))]
                            + self.__packages_to_manage_hostvars)

        if self.__python_process_required \
           and self.__family == "os":
            packages_spec = self._combine_structures(
                                [json.loads(json.dumps(packages_spec))]
                                + [self._get_python_os_packages_structure()])

        packages_all_all = []
        packages_all_version = []
        packages_distro_all = []
        packages_distro_version = []

        if "all" in packages_spec.keys():
            if "all" in packages_spec["all"].keys():
                packages_all_all = packages_spec["all"]["all"]

            if self.__distribution_version in packages_spec["all"].keys():
                packages_all_version = \
                    packages_spec["all"][self.__distribution_version]

        if self.__distribution_name in packages_spec.keys():
            packages_specs_to_apply = packages_spec[self.__distribution_name]
        elif self.__distribution_name_alias in packages_spec.keys():
            packages_specs_to_apply = \
                packages_spec[self.__distribution_name_alias]
        else:
            packages_specs_to_apply = None

        if packages_specs_to_apply is not None:
            if "all" in packages_specs_to_apply.keys():
                packages_distro_all = packages_specs_to_apply["all"]

            if self.__distribution_version in packages_specs_to_apply.keys():
                packages_distro_version = \
                    packages_specs_to_apply[self.__distribution_version]

        packages_to_process = \
            packages_all_all \
            + packages_all_version \
            + packages_distro_all \
            + packages_distro_version

        return packages_to_process

    def _setup_virtualenv(self):
        """Setup virtualenv"""
        self.__debug_info["virtualenv_created"] = False

        if self.__family == "python" \
           and (not self.__python_virtualenv_exists
                or self.__python_virtualenv_needs_upgrade):

            if self.__python_virtualenv_needs_upgrade:
                try:
                    rmtree(self.__python_virtualenv)
                except Exception:
                    raise Exception("Failed to remove virtualenv")
                self.__python_virtualenv_needs_upgrade = False

            python = self.__python_virtualenv_python

            if self.__python_virtualenv_site_packages:
                args = "--system-site-packages"
            else:
                args = ""

            if self.__python_virtualenv_command is not None:
                virtualenv_cmd = self.__python_virtualenv_command
            else:
                if int(self.__distribution_version) == 7:
                    virtualenv_cmd = "/usr/bin/virtualenv-3"
                elif int(self.__distribution_version) > 7:
                    virtualenv_cmd = "/usr/bin/virtualenv"
                else:
                    raise Exception(
                        "Cannot determine virtualenv command. "
                        "Use variable packages_python_virtualenv_command to "
                        "indicate one")

            cmd = [
                virtualenv_cmd,
                "--python=" + python,
                args,
                self.__python_virtualenv
            ]
            try:
                stdout, stderr = self._run([cmd])
            except Exception:
                if len(stdout) > 0:
                    if stdout[0].islower:
                        glue = ": "
                    else:
                        glue = ". "
                    msg = "Failed to setup virtualenv"
                    if len(stdout) > 0:
                        msg += glue + stdout
                    raise Exception(msg)

            self.__debug_info["virtualenv_created"] = True
            self.__python_virtualenv_exists = True
            self.__changed = True

    def gather(self):
        """Gather packages"""
        try:
            self._gather_os_packages()
            self._gather_os_packages_capabilites()
            self._gather_os_packages_groups()

            if self.__family == "python":
                self._gather_python()
                self._gather_virtualenv_status()
                self._setup_virtualenv()
                self._gather_python_packages()

            packages_to_manage = list()

            packages = self._get_packages_to_manage()
            for package in packages:
                name = package["name"]
                state = package["state"]
                virtualenv = package.get(
                        "virtualenv",
                        self.__python_virtualenv)
                virtualenv_command = package.get(
                        "virtualenv_command",
                        self.__python_virtualenv_command)
                virtualenv_python = package.get(
                        "virtualenv_python",
                        self.__python_virtualenv_python)
                virtualenv_site_packages = package.get(
                        "virtualenv_site_packages",
                        self.__python_virtualenv_site_packages)
                extra_args = package.get(
                        "extra_args",
                        self.__python_extra_args)

                package_dict = self._get_package_spec(
                    name,
                    state,
                    virtualenv,
                    virtualenv_command,
                    virtualenv_python,
                    virtualenv_site_packages,
                    extra_args)

                if package_dict is not None:
                    packages_to_manage = packages_to_manage + [package_dict]

            result = dict(
                changed=self.__changed, packages=packages_to_manage)

            capabilites_present = self.__packages_capabilities_present,
            ansible_facts = dict(
                _packages_capabilities_present=capabilites_present,
                _packages_groups_present=self.__packages_groups_present,
                _packages_os_present=self.__packages_os_present
            )

            if self.__family == "os":
                ansible_facts["_packages_os_managed"] = \
                    self.__packages_os_managed \
                    + packages_to_manage
                result["module"] = self.__package_module

            if self.__family == "python":
                ansible_facts["_packages_python_managed"] = \
                    self.__packages_python_managed \
                    + packages_to_manage
                ansible_facts["_packages_python_present"] = \
                    self.__packages_python_present
                ansible_facts["_packages_python_virtualenv_exists"] = \
                    self.__python_virtualenv_exists
                ansible_facts["_python_virtualenv_needs_upgrade"] = \
                    self.__python_virtualenv_needs_upgrade
                ansible_facts["_packages_python_virtualenv"] = \
                    self.__python_virtualenv
                ansible_facts["_packages_python_process_required"] = \
                    self.__python_process_required
                ansible_facts["packages_python_virtualenv_dir"] = \
                    "{path}/".format(path=self.__python_virtualenv)
                ansible_facts["packages_python_bin_dir"] = \
                    self.__python_bin_dir
                result["python_interpreter"] = self.__python_interpreter

            if self.__debug:
                result["debug_info"] = self.__debug_info

            result["ansible_facts"] = ansible_facts
        except Exception as e:
            msg = str(e)
            if msg[0].islower:
                glue = ": "
            else:
                glue = ". "
            return dict(
                failed=True, msg="Cannot gather packages info" + glue + msg)

        return result


def main():
    argument_spec = dict(
        ansible_python_interpreter=dict(type="str", default=None),
        distribution_name=dict(type="str", required=True),
        distribution_version=dict(type="str", required=True),
        distribution_aliases=dict(type="dict", required=True),
        family=dict(type="str", required=True),
        debug=dict(type="bool", default=False),
        packages_os=dict(type="dict", default={}),
        packages_os_hostvars=dict(type="list", default=[]),
        packages_os_present=dict(type="list", default=None),
        packages_os_managed=dict(type="list", default=[]),
        packages_capabilities_present=dict(type="list", default=None),
        packages_groups_present=dict(type="list", default=None),
        packages_python=dict(type="dict", default={}),
        packages_python_hostvars=dict(type="list", default=[]),
        packages_python_present=dict(type="list", default=None),
        packages_python_managed=dict(type="list", default=[]),
        python_process_required=dict(type="bool", required=True),
        python_version=dict(type="str", required=True),
        python_virtualenv=dict(type="str", required=True),
        python_virtualenv_command=dict(type="str", default=None),
        python_virtualenv_python=dict(type="str", default="/usr/bin/python3"),
        python_virtualenv_site_packages=dict(type="bool", default=True),
        python_virtualenv_exists=dict(type="bool", default=False),
        python_virtualenv_needs_upgrade=dict(type="bool", default=False),
        python_previous_virtualenv=dict(type="str", default=None),
        python_extra_args=dict(type="str", default=""),
        timeout=dict(type="int", default=60),
    )

    module = AnsibleModule(argument_spec=argument_spec)

    try:
        ansible_python_interpreter = \
            module.params["ansible_python_interpreter"]
        distribution_name = module.params["distribution_name"]
        distribution_version = module.params["distribution_version"]
        distribution_aliases = module.params["distribution_aliases"]
        family = module.params['family']
        packages_os = module.params["packages_os"]
        packages_os_hostvars = module.params["packages_os_hostvars"]
        packages_os_present = module.params["packages_os_present"]
        packages_os_managed = module.params["packages_os_managed"]
        packages_capabilities_present = \
            module.params["packages_capabilities_present"]
        packages_groups_present = \
            module.params["packages_groups_present"]
        packages_python = module.params["packages_python"]
        packages_python_hostvars = module.params["packages_python_hostvars"]
        packages_python_present = module.params["packages_python_present"]
        packages_python_managed = module.params["packages_python_managed"]
        python_process_required = module.params["python_process_required"]
        python_version = module.params["python_version"]
        python_virtualenv = module.params["python_virtualenv"]
        python_virtualenv_command = module.params["python_virtualenv_command"]
        python_virtualenv_python = module.params["python_virtualenv_python"]
        python_virtualenv_site_packages = \
            module.params["python_virtualenv_site_packages"]
        python_virtualenv_exists = module.params["python_virtualenv_exists"]
        python_virtualenv_needs_upgrade = \
            module.params["python_virtualenv_needs_upgrade"]
        python_previous_virtualenv = \
            module.params["python_previous_virtualenv"]
        python_extra_args = module.params["python_extra_args"]
        timeout = module.params["timeout"]
        debug = module.params["debug"]

        pm = PackagesManager(
            ansible_python_interpreter,
            distribution_name,
            distribution_version,
            distribution_aliases,
            family,
            packages_os,
            packages_os_hostvars,
            packages_os_present,
            packages_os_managed,
            packages_capabilities_present,
            packages_groups_present,
            packages_python,
            packages_python_hostvars,
            packages_python_present,
            packages_python_managed,
            python_process_required,
            python_version,
            python_virtualenv,
            python_virtualenv_command,
            python_virtualenv_python,
            python_virtualenv_site_packages,
            python_virtualenv_exists,
            python_virtualenv_needs_upgrade,
            python_previous_virtualenv,
            python_extra_args,
            timeout,
            debug)

        result = pm.gather()
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=str(e), exception=format_exc())


if __name__ == '__main__':
    main()
