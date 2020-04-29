==========
MDRewriter
==========

When VaRA creates blame annotated ``.ll``/``.bc`` files, it embeds absolute paths to the found git repositories.
This is helpful when you directly want to analyze the generated file on the same system.
However, the embedded paths can lead to trouble/errors when moving files to other systems that do not have the correct repository in the specified location.
To circumvent this problem, the ``MDRewriter`` pass provides a convenient way to change the embedded path.
Just add the ``MDRewriter`` to the pass pipeline and provided an alternative path mapping for the repositories with `-vara-git-mappings`.
The path mapping is a comma separated list of tuples :code:`"repo_name:/new/path"` of repo paths that should be replaced.

For example:

.. code-block:: bash

  bin/opt -vara-rewriteMD -vara-git-mappings="repo_name:/new/path/","sub_repo:/new/path" ...  input.ll
