vara-config
===========

With this tool, you can view and modify the configuration of the tool suite.

.. program-output:: vara-config -h
    :nostderr:


With `vara-config set`, you can set one or multiple config options at once:

.. program-output:: vara-config set -h
    :nostderr:


.. note::

    The config is organized in a hierarchical structure. The `vara-config` tool
    uses a path-like notation to find options in this config-tree, e.g.,
    `paper_config/folder` refers to the `folder` option in the `paper_config`
    sub-config.


You can view specific parts of the config or the complete config with
`vara-config show`:

.. program-output:: vara-config show -h
    :nostderr:


.. note::

    You can print larger sub-trees of the config by passing partial paths to
    `vara-config show`.
