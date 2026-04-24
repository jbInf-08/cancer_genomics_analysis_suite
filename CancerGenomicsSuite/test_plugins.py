#!/usr/bin/env python3
"""Test the plugin registry with demo module."""

from plugin_registry import get_registered_plugins

plugins = get_registered_plugins()
print(f'Loaded {len(plugins)} plugins')

for name, data in plugins.items():
    print(f'  - {name}: {data["metadata"]["description"]}')
