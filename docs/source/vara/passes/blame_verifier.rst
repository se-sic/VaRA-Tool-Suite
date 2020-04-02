Run Blame-MD-Verifier
=====================

`TODO (se-passau/VaRA#587) <https://github.com/se-passau/VaRA/issues/587>`_: write docs

Run Blame-MD-Verifier with flags:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All llvm-opt vara flags start with -vara-{FLAG}:

   .. code-block::

      llvm/opt Detections
      └── verify-blameMD                  # Activate BlameMDVerifier
          └── verifier-options=           # Choose between multiple print options
              ├── Status                  # Print if the module as a whole passed or failed
              ├── All                     # Print all
              ├── Fails                   # Print all fails
              ├── Passes                  # Print all passes
              └── Stop                    # Print till fail