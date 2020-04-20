Python Scripting Tips
=====================

This page contains a few useful code snippets and tips for our python scripts.

Load VaRA Config
----------------

.. code-block::

   import os
   import sys
   import importlib.util
   from pathlib import Path


   def load_vara_config(rel_path: str) -> 'module':
       ''' Load VaRA config from a given path (relative to this module). '''
       current_dir = os.path.dirname(os.path.abspath(__file__))
       vara_config_file = Path(current_dir) / rel_path

       module_spec = importlib.util.spec_from_file_location("__main__", vara_config_file)
       module = importlib.util.module_from_spec(module_spec)

       old_stdout = sys.stdout
       sys.stdout = open(os.devnull, "w")

       module_spec.loader.exec_module(module)

       sys.stdout.close()
       sys.stdout = old_stdout

       return module


   def main() -> None:
       # load vara config dictionary (path relative from this file)
       vara_config = load_vara_config(r'../../.vara-config.py')
       vara_config_dict = vara_config.get_config_variables()

Force minimum python version
----------------------------

.. code-block::

   import sys


   MIN_PYTHON = (3, 6)


   def main() -> None:
       if sys.version_info < MIN_PYTHON:
           sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

Temporary directory with 'with' statement
-----------------------------------------

.. code-block::

   import os
   import contextlib
   import tempfile
   import shutil


   @contextlib.contextmanager
   def cd(newdir, cleanup=lambda: True):
       """ Change into a new directory. """
       prevdir = os.getcwd()
       os.chdir(os.path.expanduser(newdir))
       try:
           yield
       finally:
           os.chdir(prevdir)
           cleanup()


   @contextlib.contextmanager
   def tempdir():
       """ Create a temp. directory and cd into it. """
       dirpath = tempfile.mkdtemp()
       def cleanup():
           shutil.rmtree(dirpath)
       with cd(dirpath, cleanup):
           yield dirpath


   def main() -> None:
       with tempdir() as dirpath:
           # do stuff