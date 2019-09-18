# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


def packages_normalize_spec(spec):
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
                        normalized_item = {"name": list(subitem.keys())[0],
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


def packages_combine_specs(specs):
    """Combine the a list of spects into one dict

    Args:
        specs (list): dicts with specs to combine

    Returns:
        dict: combined specs
    """
    normalized_specs = []
    for spec in specs:
        normalized_specs.append(packages_normalize_spec(spec))

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


class FilterModule(object):
    """Ansible packages filters."""

    def filters(self):
        return {
            "packages_combine_specs": packages_combine_specs
        }
