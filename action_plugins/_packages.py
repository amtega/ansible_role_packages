#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.plugins.filter.core import combine, to_json
from ansible.plugins.test.core import version_compare
from ansible.utils.display import Display
import json
import re


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    _display = Display()

    def _get_task_var(self, name, default=None):
        """Get templated task variable"""

        if name in self.__task_vars:
            ret = self._templar.template(self.__task_vars.get(name))
        else:
            ret = default

        return ret

    def _action(self, action="_packages", args={}):
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

    def _get_fact(self, name, default=None):
        """Get a fact"""

        result = self.__ansible_facts.get(name,
                                          self.__ansible_facts.get(default))
        return result

    def _gather_module_params(self):
        """Gather module parameters"""

        self.__family = self._task.args.get("family")

    def _gather_role_vars(self):
        """Gather role vars"""

        self.__packages_debug = \
            self._get_task_var("packages_debug", False)

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

        self.__packages_python_source_install_dir = \
            self._get_task_var("packages_python_source_install_dir", None)

    def _gather_facts(self):
        """Gather facts"""

        self.__debug_info["facts_gathered"] = False
        self.__ansible_facts = self._get_task_var("ansible_facts", {})
        self.__ansible_facts_gathered = False
        if "python_version" not in self.__ansible_facts.keys():
            self.__debug_info["facts_gathered"] = True
            result = self._execute_module(module_name="setup",
                                          module_args=dict(),
                                          task_vars=self.__task_vars)
            self.__ansible_facts = result["ansible_facts"]
            self.__ansible_facts_gathered = True

    def _gather_distribution_info(self):
        """Gather distribution info"""

        self.__distro_name = self._get_fact("ansible_distribution",
                                            "distribution").lower()
        self.__distro_name_alias = self.__packages_distribution_aliases.get(
                    self.__distro_name,
                    self.__distro_name).lower()
        self.__distro_version = \
            str(self._get_fact("ansible_distribution_major_version",
                               "distribution_major_version")).lower()

    def _gather_packages_module(self):
        """Gather packages module"""

        if self.__distro_name in ["centos", "redhat"]:
            self.__package_module = "yum"
        else:
            self.__package_module = "dnf"

    def _gather_python_info(self):
        """Gather python info"""

        self.__python_version_major = \
            self.__ansible_facts["python"]["version"]["major"]

        self.__python_interpreter = "{virtualenv_path}/bin/python".format(
                        virtualenv_path=self.__packages_python_virtualenv)

    def _gather_private_facts(self):
        """Gather private facts"""

        self.__packages_os_managed = \
            self.__ansible_facts.get("_packages_os_managed", [])

        self.__packages_python_managed = \
            self.__ansible_facts.get("_packages_python_managed", [])

        self.__packages_virtualenv_exists = \
            self.__ansible_facts.get("_packages_virtualenv_exists", None)

        self.__packages_virtualenv_needs_upgrade = \
            self.__ansible_facts.get("__packages_virtualenv_needs_upgrade",
                                     None)

        self.__packages_python_virtualenv_previous = \
            self.__ansible_facts.get("_packages_python_virtualenv", None)

    def _gather_package_management_info(self):
        """Gather package management info"""

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

    def _gather_os_packages(self):
        """Gather os packages"""

        self.__packages_os_present = list()

        self.__debug_info["packages_os_gathered"] = False
        if "packages" not in self.__ansible_facts:
            self.__debug_info["packages_os_gathered"] = True
            result = self._execute_module(module_name="package_facts",
                                          module_args=dict(),
                                          task_vars=self.__task_vars)

            self.__package_facts = result["ansible_facts"]["packages"]
        else:
            self.__package_facts = self.__ansible_facts["packages"]

        self.__packages_os_present = \
            self.__packages_os_present \
            + list(self.__package_facts.keys())

        if self.__family == "os":
            self.__packages_present = self.__packages_os_present

    def _gather_os_packages_capabilites(self):
        """Gather los packages capabilities"""

        self.__capabilities_present = \
            self.__ansible_facts.get("_packages_capabilities_present", None)

        self.__debug_info["capabilites_gathered"] = False
        if self.__capabilities_present is None:
            self.__debug_info["capabilites_gathered"] = True
            cmd = "/usr/bin/rpm -qa --provides | cut -d = -f 1"
            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd, _uses_shell=True))
            result = action.run(task_vars=self.__task_vars)
            self.__capabilities_present = \
                list((p.strip() for p in result["stdout_lines"]))

        self.__packages_os_present = \
            self.__packages_os_present \
            + self.__capabilities_present

        if self.__family == "os":
            self.__packages_present = self.__packages_os_present

    def _gather_os_packages_groups(self):
        """Gather os packages groups"""

        self.__groups_present = \
            self.__ansible_facts.get("_packages_groups_present", None)

        self.__debug_info["groups_gathered"] = False
        if self.__groups_present is None:
            self.__groups_present = list()

            if version_compare(self.__distro_version, "6", ">"):
                self.__debug_info["groups_gathered"] = True
                cmd = "LANGUAGE=en_US yum group list"
                action = self._action(action="shell",
                                      args=dict(_raw_params=cmd,
                                                _uses_shell=True))
                result = action.run(task_vars=self.__task_vars)

                if "stdout_lines" in result:
                    lines = result["stdout_lines"]
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
                            self.__groups_present.append("@" + line.strip())

        self.__packages_os_present = \
            self.__packages_os_present \
            + self.__groups_present

        if self.__family == "os":
            self.__packages_present = \
                self.__packages_present + self.__groups_present

    def _gather_python_os_packages(self):
        """Gather python os packages"""

        if version_compare(self.__distro_version, "7", ">="):
            self.__python_os_package = "python3"
            self.__pip_os_package = "python3-pip"
            self.__virtualenv_os_package = "python3-virtualenv"
            self.__setup_tools_os_package = "python3-setuptools"
        else:
            self.__python_os_package = None
            self.__pip_os_package = None
            self.__virtualenv_os_package = None
            self.__setup_tools_os_package = None

    def _gather_python_packages(self):
        """Gather python packages"""

        self.__packages_python_present = \
            self.__ansible_facts.get("_packages_python_present", None)

        self.__debug_info["packages_python_gathered"] = False
        if self.__family == "python" \
           and (self.__packages_python_present is None
                or (self.__packages_python_virtualenv_previous is not None
                    and self.__packages_python_virtualenv_previous
                    != self.__packages_python_virtualenv)):

            self.__packages_python_managed = []
            self.__packages_managed = []

            if len(self.__packages_python_virtualenv) > 0:
                packages_pip_dir = "{virtualenv}/bin/".format(
                                virtualenv=self.__packages_python_virtualenv)
            else:
                packages_pip_dir = \
                    self.__ansible_facts["packages_python_bin_dir"]

            self.__debug_info["packages_python_gathered"] = True
            cmd = packages_pip_dir + "pip list | awk '{ print $1 };'"
            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd, _uses_shell=True))
            result = action.run(task_vars=self.__task_vars)
            self.__packages_python_present = \
                list((p.strip() for p in result["stdout_lines"]))

        if self.__family == "python":
            self.__packages_present = self.__packages_python_present

    def _gather_virtualenv_status(self):
        """Gather virtualenv status"""

        if self.__family == "python" \
           and self.__packages_virtualenv_exists is None:
            cmd = "{python} "\
                  "-c 'from sys import version_info ; print(version_info[0])'"\
                  .format(python=self.__python_interpreter)

            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd,
                                            _uses_shell=False))
            result = action.run(task_vars=self.__task_vars)

            virtualenv_status_error = result.get("stderr", None)
            virtualenv_status_major = result.get("stdout", None)
            self.__packages_virtualenv_exists = False

            if len(virtualenv_status_error) == 0:
                self.__packages_virtualenv_exists = True

            if len(virtualenv_status_major) > 0 \
               and version_compare(virtualenv_status_major, "3", "<"):
                self.__packages_virtualenv_needs_upgrade = True
            else:
                self.__packages_virtualenv_needs_upgrade = False

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
        """Combine the a list of packags structures into one dict

        Args:
            structures (list): dicts with packages structures to combine

        Returns:
            dict: combined structures
        """

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
           and self.__python_os_package not in self.__package_facts.keys():
            self.__python_os_packages = \
                [dict(name=self.__python_os_package,
                      state="present")]
        else:
            self.__python_os_packages = list()

        if self.__pip_os_package is not None \
           and self.__pip_os_package not in self.__package_facts.keys():
            self.__python_os_packages = \
                self.__python_os_packages \
                + [dict(name=self.__pip_os_package,
                        state="present")]

        if self.__setup_tools_os_package is not None \
           and self.__setup_tools_os_package \
                not in self.__package_facts.keys():
            self.__python_os_packages = \
                self.__python_os_packages \
                + [dict(name=self.__setup_tools_os_package,
                        state="present")]

        if self.__virtualenv_os_package is not None \
           and self.__virtualenv_os_package not in self.__package_facts.keys():
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

        return result

    def _get_packages_to_manage(self):
        """Get packages to manage"""

        packages_spec = self._combine_structures(
                            [json.loads(to_json(self.__packages_to_manage))]
                            + self.__packages_to_manage_hostvars)

        if self.__packages_python_process_required \
           and self.__family == "os":
            packages_spec = self._combine_structures(
                                [json.loads(to_json(packages_spec))]
                                + [self._get_python_os_packages_structure()])

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

    def _setup_virtualenv(self):
        """Setup virtualenv"""

        self.__debug_info["virtualenv_created"] = False
        if self.__family == "python" \
           and (not self.__packages_virtualenv_exists
                or self.__packages_virtualenv_needs_upgrade):

            if self.__packages_virtualenv_needs_upgrade:
                result = self._execute_module(
                        module_name="file",
                        module_args=dict(
                                        path=self.__packages_python_virtualenv,
                                        state="absent"),
                        task_vars=self.__task_vars)

                if result.get("failed", False):
                    raise AnsibleError("Failed to remove virtualenv")

                self.__packages_virtualenv_needs_upgrade = False

            if self.__packages_python_virtualenv_python is not None:
                python = self.__packages_python_virtualenv_python
            else:
                if version_compare(self.__distro_version, "7", "<"):
                    python = "{path}/bin/python3".format(
                            path=self.__packages_python_source_install_dir)
                else:
                    python = "/usr/bin/python3"

            if self.__packages_python_virtualenv_site_packages:
                args = "--system-site-packages"
            else:
                args = ""

            if self.__packages_python_virtualenv_command is not None:
                virtualenv_cmd = self.__packages_python_virtualenv_command
            else:
                if version_compare(self.__distro_version, "7", "="):
                    virtualenv_cmd = "/usr/bin/virtualenv-3"
                elif version_compare(self.__distro_version, "7", ">"):
                    virtualenv_cmd = "/usr/bin/virtualenv"
                else:
                    virtualenv_cmd = \
                        self.__packages_python_source_install_dir \
                        + "/bin/virtualenv"

            cmd = "{virtualenv_cmd} " \
                  "--python={python} {args} {virtualenv}" \
                .format(virtualenv_cmd=virtualenv_cmd,
                        python=python,
                        args=args,
                        virtualenv=self.__packages_python_virtualenv)

            action = self._action(action="shell",
                                  args=dict(_raw_params=cmd,
                                            _uses_shell=False))

            task_vars = self.__task_vars.copy()
            task_vars["ansible_python_interpreter"] = \
                self.__packages_python_virtualenv_python

            result = action.run(task_vars=task_vars)

            if result.get("failed", False):
                raise AnsibleError("Failed to setup virtualenv")

            self.__debug_info["virtualenv_created"] = True
            self.__packages_virtualenv_exists = True

            self.__changed = True

    def _gather(self, *args, **kwargs):
        """Gather info"""

        self._gather_module_params()
        self._gather_role_vars()
        self._gather_facts()
        self._gather_distribution_info()
        self._gather_packages_module()
        self._gather_python_info()
        self._gather_private_facts()
        self._gather_package_management_info()
        self._gather_os_packages()
        self._gather_os_packages_capabilites()
        self._gather_os_packages_groups()
        self._gather_python_os_packages()

        if self.__family == "python":
            self._gather_virtualenv_status()
            self._setup_virtualenv()
            self._gather_python_packages()

    def run(self, tmp=None, task_vars=None):
        """Run the action module"""

        super(ActionModule, self).run(tmp, task_vars)

        self.__tmp = tmp
        self.__task_vars = task_vars
        self.__changed = False
        self.__debug_info = dict()

        try:
            self._gather()

            packages_to_manage = list()

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

                package_dict = self._get_package_spec(name,
                                                      state,
                                                      virtualenv,
                                                      virtualenv_command,
                                                      virtualenv_python,
                                                      virtualenv_site_packages,
                                                      extra_args)

                if package_dict is not None:
                    packages_to_manage = packages_to_manage + [package_dict]

            action_result = dict(changed=self.__changed,
                                 packages=packages_to_manage)

            ansible_facts = dict(
                _packages_capabilities_present=self.__capabilities_present,
                _packages_groups_present=self.__groups_present,
                packages=self.__package_facts
            )

            if self.__family == "os":
                ansible_facts["_packages_os_managed"] = \
                    self.__packages_os_managed \
                    + packages_to_manage
                action_result["module"] = self.__package_module

            if self.__family == "python":
                ansible_facts["_packages_python_managed"] = \
                    self.__packages_python_managed \
                    + packages_to_manage
                ansible_facts["_packages_python_present"] = \
                    self.__packages_python_present
                ansible_facts["_packages_virtualenv_exists"] = \
                    self.__packages_virtualenv_exists
                ansible_facts["__packages_virtualenv_needs_upgrade"] = \
                    self.__packages_virtualenv_needs_upgrade
                ansible_facts["_packages_python_virtualenv"] = \
                    self.__packages_python_virtualenv
                ansible_facts["packages_python_virtualenv_dir"] = \
                    "{path}/".format(path=self.__packages_python_virtualenv)
                ansible_facts["packages_python_bin_dir"] = \
                    "{path}/bin/".format(
                                        path=self.__packages_python_virtualenv)

                action = self._action(
                    action="set_fact",
                    args=dict(
                        ansible_python_interpreter=self.__python_interpreter))
                action.run(task_vars=self.__task_vars)

                action_result["python_interpreter"] = self.__python_interpreter

            if self.__ansible_facts_gathered:
                ansible_facts = combine(self.__ansible_facts, ansible_facts)

            if self.__packages_debug:
                action_result["debug"] = self.__debug_info

            action_result["ansible_facts"] = ansible_facts

        finally:
            self._remove_tmp_path(self._connection._shell.tmpdir)

        return action_result
