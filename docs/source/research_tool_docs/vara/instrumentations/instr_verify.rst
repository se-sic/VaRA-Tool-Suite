Instrumentation Verifier (``instr_verify``)
===========================================

The instrumentation verifier is an instrumentation built to debug and verify regions.
The verifier checks if every start instrumentation for a region has a matching end instrumentation.
Should a region instrumented incorrectly, the verifier reports the problem and provides extra information about the region, e.g., the region ID or the file location of the code region (in case the code was compiled with ``-g``).

Example output:

.. code-block:: console

   Entered region: 8646911284552155138
   Left region: 8646911284552155138
   Entered region: 8646911284552171523
   Left region: 8646911284552171523
   Finalization: Success
   ---------------------
