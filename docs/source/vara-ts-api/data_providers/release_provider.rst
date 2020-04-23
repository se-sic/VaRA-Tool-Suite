Release Provider
----------------

This provider allows access to the release revisions of a project.
The default implementation works for projects following the versioning scheme specified in :ref:`PEP 440<https://www.python.org/dev/peps/pep-0440/>`.
Alternatively, a :class:`hook<varats.data.provider.release.release_provider.ReleaseProviderHook>` can be used for custom release lookup logic.

.. automodule:: varats.data.provider.release.release_provider
    :members:
    :undoc-members:
    :show-inheritance:
