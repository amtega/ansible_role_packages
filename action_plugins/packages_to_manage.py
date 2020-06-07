#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.plugins.filter.core import to_json
from ansible.plugins.test.core import version_compare
from ansible.utils.display import Display
import json
import re


class ActionModule(ActionBase):
    _display = Display()

    def _gather(self, *args, **kwargs):
        # Gather module Variables

        self.__family = self._task.args.get("family")

        # Gather role variables

        self.__packages_os = \
            self._get_task_var("packages_os")

        self.__packages_python = \
            self._get_task_var("packages_python")

        self.__packages_os_hostvars = \
            self._get_task_var("packages_os_hostvars", [])

        self.__packages_python_hostvars = \
            self._get_task_var("packages_python_hostvars", [])

        self.__packages_distribution_aliases = \
            self._get_task_var("packages_distribution_aliases")

        self.__packages_python_process_required = \
            self._get_task_var("packages_python_process_required")

        self.__packages_python_virtualenv = \
            self._get_task_var("packages_python_virtualenv", None)

        self.__packages_python_virtualenv_command = \
            self._get_task_var("packages_python_virtualenv_command", None)

        self.__packages_python_virtualenv_python = \
            self._get_task_var("packages_python_virtualenv_python", None)

        self.__packages_python_virtualenv_site_packages = \
            self._get_task_var("packages_python_virtualenv_site_packages",
                               None)

        self.__packages_python_extra_args = \
            self._get_task_var("packages_python_extra_args", None)

        # Gather facts

        self.__ansible_facts = self._get_task_var("ansible_facts")

        # Gather distro info

        self.__distro_name = self.__ansible_facts["distribution"].lower()
        self.__distro_name_alias = self.__packages_distribution_aliases.get(
                    self.__distro_name,
                    self.__distro_name).lower()
        self.__distro_version = \
            str(self.__ansible_facts['distribution_major_version']).lower()

        # Gather python info

        self.__python_version_major = \
            self.__ansible_facts["python"]["version"]["major"]

        # Gather internal facts

        self.__packages_os_managed = \
            self.__ansible_facts.get("_packages_os_managed", [])

        self.__packages_python_managed = \
            self.__ansible_facts.get("_packages_python_managed", [])

        # Gather packages to manage, packages from hostvars, packages already
        # managed and packages already present

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

    def _get_task_var(self, name, default=None):
        """Get templated task variable"""

        if name in self._task_vars:
            ret = self._templar.template(self._task_vars.get(name))
        else:
            ret = default

        return ret

    def _action(self, action="tower_api_rest", args={}):
        """Return a new ansible action"""

        task = self._task.copy()

        task.args = dict()
        for key in args.keys():
            task.args[key] = args[key]

        action = self._shared_loader_obj.action_loader.get(
            action,
            task=task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj
        )

        return action

    def _gather_facts(self):
        if "python_version" not in self.__ansible_facts:
            self._execute_module(module_name="setup",
                                 module_args=dict(),
                                 task_vars=self._task_vars)

    def _gather_packages(self):
        self.__packages_os_present = list()

        if "packages" not in self.__ansible_facts:
            result = self._execute_module(module_name="package_facts",
                                          module_args=dict(),
                                          task_vars=self._task_vars)

            self.__package_facts = result["ansible_facts"]["packages"]
        else:
            self.__package_facts = self.__ansible_facts["packages"]

        self.__packages_os_present = \
            self.__packages_os_present \
            + list(self.__package_facts.keys())

        if self.__family == "os":
            self.__packages_present = self.__packages_os_present

    def _gather_capabilites(self):
        self.__capabilities_present = \
            self.__ansible_facts.get("_packages_capabilities_present", None)

        if self.__capabilities_present is None:
            cmd = "/usr/bin/rpm -qa --provides | cut -d = -f 1"
            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd, _uses_shell=True))
            result = action.run(task_vars=self._task_vars)
            self.__capabilities_present = \
                list((p.strip() for p in result["stdout_lines"]))

        self.__packages_os_present = \
            self.__packages_os_present \
            + self.__capabilities_present

    def _gather_groups(self):
        self.__groups_present = \
            self.__ansible_facts.get("_packages_groups_present", None)

        if self.__groups_present is None:
            self.__groups_present = list()

            if version_compare(
                            self.__ansible_facts["distribution_major_version"],
                            "6",
                            ">"):
                cmd = "LANGUAGE=en_US yum group list"
                action = self._action(action="shell",
                                      args=dict(_raw_params=cmd,
                                                _uses_shell=True))
                result = action.run(task_vars=self._task_vars)

                if "stdout_lines" in result:
                    lines = result["stdout_lines"]
                    regex_installed = re.compile("^Installed")
                    regex_available = re.compile("^Available")
                    regex_group = re.compile("^   ")

                    gather_groups = False
                    for l in lines:
                        if regex_installed.match(l):
                            gather_groups = True
                        elif regex_available.match(l):
                            gather_groups = False
                        elif regex_group.match(l) and gather_groups:
                            self.__groups_present.append("@" + l.strip())

        self.__packages_os_present = \
            self.__packages_os_present \
            + self.__groups_present

        if self.__family == "os":
            self.__packages_present = \
                self.__packages_present + self.__groups_present

    def _gather_python_os_packages(self):
        if version_compare(self.__distro_version, "7", ">="):
            self.__pip_os_package = "python{version}-pip".format(
                                version=str(self.__python_version_major))
        else:
            self.__pip_os_package = "python-pip"

        if version_compare(self.__python_version_major, "3", "<"):
            self.__virtualenv_os_package = "python-virtualenv"
        else:
            self.__virtualenv_os_package = \
                "python{version}-virtualenv".format(
                                version=str(self.__python_version_major))

        if version_compare(self.__python_version_major, "3", "<"):
            self.__setup_tools_os_package = "python-setuptools"
        else:
            self.__setup_tools_os_package = \
                "python{version}-setuptools".format(
                                version=str(self.__python_version_major))

    def _gather_python_packages(self):
        self.__packages_python_present = \
            self.__ansible_facts.get("_packages_python_present", None)

        if self.__family == "python" \
           and self.__packages_python_present is None:
            if len(self.__packages_python_virtualenv) > 0:
                packages_pip_dir = "{virtualenv}/bin/".format(
                                virtualenv=self.__packages_python_virtualenv)
            else:
                packages_pip_dir = \
                    self.__ansible_facts["packages_python_bin_dir"]

            cmd = packages_pip_dir + "pip list | awk '{ print $1 };'"
            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd, _uses_shell=True))
            result = action.run(task_vars=self._task_vars)
            self.__packages_python_present = \
                list((p.strip() for p in result["stdout_lines"]))

        if self.__family == "python":
            self.__packages_present = self.__packages_python_present

    def _gather_os_info(self):
        self._gather_facts()
        self._gather_packages()
        self._gather_capabilites()
        self._gather_groups()
        self._gather_python_os_packages()
        self._gather_python_packages()

    def _normalize_spec(self, spec):
        """Normalize packages spec to list

        Args:
            spec (dict): packages spec

        Returns:
            dict: packages spec normalized
        """

        normalized_spec = {}
        for distribution in spec:
            for release in spec[distribution]:
                item = spec[distribution][release]
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

                if distribution not in normalized_spec.keys():
                    normalized_spec[distribution] = {}

                if release not in normalized_spec[distribution]:
                    normalized_spec[distribution][release] = normalized_items
                else:
                    normalized_spec[distribution][release] += normalized_items

        return normalized_spec

    def _combine_specs(self, specs):
        """Combine the a list of spects into one dict

        Args:
            specs (list): dicts with specs to combine

        Returns:
            dict: combined specs
        """

        normalized_specs = []
        for spec in specs:
            normalized_specs.append(self._normalize_spec(spec))

        combined_specs = {}
        for spec in normalized_specs:
            for distribution in spec:
                for release in spec[distribution]:
                    spec_packages = spec[distribution][release]

                    if distribution not in combined_specs.keys():
                        combined_specs[distribution] = {}

                    if release not in combined_specs[distribution].keys():
                        combined_specs[distribution][release] = []

                    combined_specs[distribution][release] += spec_packages

        return combined_specs

    def _get_python_os_packages_spec(self):
        if self.__pip_os_package \
           not in self.__package_facts.keys():
            self.__python_os_packages = \
                [dict(name=self.__pip_os_package, state="present")]
        else:
            self.__python_os_packages = list()

        if self.__setup_tools_os_package \
           not in self.__package_facts.keys():
            self.__python_os_packages = \
                self.__python_os_packages \
                + [dict(name=self.__setup_tools_os_package,
                        state="present")]

        if self.__virtualenv_os_package not in self.__package_facts.keys():
            self.__python_os_packages = \
               self.__python_os_packages \
               + [dict(name=self.__virtualenv_os_package,
                       state="present")]

        return dict(all=dict(all=self.__python_os_packages))

    def _get_package_dict(self,
                          name,
                          state,
                          virtualenv=None,
                          virtualenv_command=None,
                          virtualenv_python=None,
                          virtualenv_site_packages=None,
                          extra_args=None):

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

        return result

    def _get_packages_to_manage(self):
        packages_spec = self._combine_specs(
                            [json.loads(to_json(self.__packages_to_manage))]
                            + self.__packages_to_manage_hostvars)

        if self.__packages_python_process_required \
           and self.__family == "os":
            packages_spec = self._combine_specs(
                                    [json.loads(to_json(packages_spec))]
                                    + [self._get_python_os_packages_spec()])

        packages_all_all = []
        packages_all_version = []
        packages_distro_all = []
        packages_distro_version = []

        if "all" in packages_spec.keys():
            if "all" in packages_spec["all"].keys():
                packages_all_all = packages_spec["all"]["all"]

            if self.__distro_version in packages_spec["all"].keys():
                packages_all_version = \
                    packages_spec["all"][self.__distro_version]

        if self.__distro_name in packages_spec.keys():
            packages_specs_to_apply = packages_spec[self.__distro_name]
        elif self.__distro_name_alias in packages_spec.keys():
            packages_specs_to_apply = packages_spec[self.__distro_name_alias]
        else:
            packages_specs_to_apply = None

        if packages_specs_to_apply is not None:
            if "all" in packages_specs_to_apply.keys():
                packages_distro_all = packages_specs_to_apply["all"]

            if self.__distro_version in packages_specs_to_apply.keys():
                packages_distro_version = \
                    packages_specs_to_apply[self.__distro_version]

        packages_to_process = \
            packages_all_all \
            + packages_all_version \
            + packages_distro_all \
            + packages_distro_version

        return packages_to_process

    def _call(self):
        self._gather()
        self._gather_os_info()
        result = list()

        packages = self._get_packages_to_manage()
        for package in packages:
            name = package["name"]
            state = package["state"]
            virtualenv = package.get(
                    "virtualenv",
                     self.__packages_python_virtualenv)
            virtualenv_command = package.get(
                    "virtualenv_command",
                    self.__packages_python_virtualenv_command)
            virtualenv_python = package.get(
                    "virtualenv_python",
                    self.__packages_python_virtualenv_python)
            virtualenv_site_packages = package.get(
                    "virtualenv_site_packages",
                    self.__packages_python_virtualenv_site_packages)
            extra_args = package.get(
                    "extra_args",
                    self.__packages_python_extra_args)

            package_dict = self._get_package_dict(name,
                                                  state,
                                                  virtualenv,
                                                  virtualenv_command,
                                                  virtualenv_python,
                                                  virtualenv_site_packages,
                                                  extra_args)

            if package_dict is not None:
                result = result + [package_dict]

        ansible_facts = dict(
            _packages_capabilities_present=self.__capabilities_present,
            _packages_groups_present=self.__groups_present,
            packages=self.__package_facts
        )

        if self.__family == "os":
            ansible_facts["_packages_os_managed"] = \
                self.__packages_os_managed \
                + result

        if self.__family == "python":
            ansible_facts["_packages_python_managed"] = \
                self.__packages_python_managed \
                + result
            ansible_facts["_packages_python_present"] = \
                self.__packages_python_present

        return dict(packages=result,
                    ansible_facts=ansible_facts)

    def run(self, tmp=None, task_vars=None):
        """Run the action module"""

        super(ActionModule, self).run(tmp, task_vars)
        self._tmp = tmp
        self._task_vars = task_vars
        return self._call()
