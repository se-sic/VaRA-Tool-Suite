Blame-MD-Verifier
=================

The Blame-Verifier is designed to analyse repositories in order to find inconsistencies between VaRA-commit-hashes and debug-commit-hashes.
It accesses the IRegion of an instruction in a module to gain the VaRA-hash and compares it with the Debug-hash, which is gained through accessing the debug information in an instruction.
The Blame-Verifier comes with a set of verifier-options, which can be used to filter the printed results of the analysis.

Run Blame-MD-Verifier
---------------------

The existence of ``llvm-debug-information`` in the used ``IR``-file is a requirement to assure a correct comparison between commit hashes.

To use the Blame-Verifier, you first have to enable the Blame Detection in your ``opt`` build with ``-vara-BD`` and activate the verifier itself with ``-vara-verify-blameMD``. To let the Blame Detection initialize the commits for repositories use ``-vara-init-commits`` in addition. Optionally you can add ``verifier-options``, which are listed below, with ``-verifier-options=Your_Option`` to filter the results. If the ``verifier-options`` are used but none is chosen explicitly, it will default to the ``Status``-option.

An example of how the Blame-Verifier can be used on a ``.ll`` file:

   .. code-block::

      ./bin/opt -vara-BD -vara-verify-blameMD -vara-init-commits -vara-verifier-options=All TestFile.ll


Verifier-options:
^^^^^^^^^^^^^^^^^

All llvm-opt vara flags start with -vara-{FLAG}:

   .. code-block::

      llvm/opt Detections
      └── BD                                 # Blame Detection
          ├── vara-init-commits              # Let's the Blame Detection initialize Commit for Repos
          └── verify-blameMD                 # Activate BlameMDVerifier
              └── verifier-options           # Choose between multiple print options
                 ├── Status                  # Print if the module as a whole passed or failed
                 ├── All                     # Print all
                 ├── Fails                   # Print all fails
                 ├── Passes                  # Print all passes
                 └── Stop                    # Print till fail
