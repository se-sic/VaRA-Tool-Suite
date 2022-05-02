Feature Performance Analysis
============================

VaRA's feature performance analysis is built to make the impact of software features measurable.
By only specifying where control variables are, our analysis pipeline detects feature-dependent code parts and instruments them for further run-time analysis.


How to set up and use the feature performance analysis
------------------------------------------------------

Setting up our analysis is simple and can be done in a few steps.

1) Set up VaRA by following our :ref:`setup guide<Build VaRA with vara-buildsetup>`.
************************************************************************************


2) Specify our modified compiler as `CC` or `CXX`.
**************************************************

.. code-block:: console

    CC=$PATH_TO_VARA_ROOT/tools/VaRA/bin/clang
    CXX=$PATH_TO_VARA_ROOT/tools/VaRA/bin/clang++


3) Set the feature specific compile flags as (`C_FLAGS` or `CXX_FLAGS`).
************************************************************************

Enable the automatic feature detection (`-fvara-feature`) and select the desired instrumentation code (`-fvara-instr=`).
The different instrumentation options can be found :ref:`here<Instrumentations>`.

.. code-block:: console

    CXX_FLAGS="$CXX_FLAGS -fvara-feature -fsanitize=vara -fvara-instr=trace_event"


(Recommended) Configure your project to use link-time optimization (LTO) for more precise analysis results.
Without LTO, the analysis can only run within a translation unit, hence, features that are used across different translation units can not be correctly analyzed.

.. code-block:: console

    CXX_FLAGS="$CXX_FLAGS -flto"
    LDFLAGS="-fuse-ld=lld"


(Optional) Pass in the location of the feature model with `-fvara-fm-path=`.
The feature model defines high-level software features ein their dependencies, together with a mapping to the variables that control the functionality in the program.
For more information, see our `collection of feature models <https://github.com/se-sic/ConfigurableSystems>`_ for different configurable software system or our `feature library <https://github.com/se-sic/vara-feature>`_.

.. code-block:: console

    CXX_FLAGS="$CXX_FLAGS -fvara-fm-path=/path/to/the/feature_model.xml"


Or, specify feature location within your code direclty.
We can mark variables as feature variable to tell the analysis that this specific variable controls the activation of feature code, in cases where the software does not provide a feature model or the developers want to explicitly encode this information.

.. code-block:: cpp

    bool MyFeatureVariable __attribute__((feature_variable("FEATURE_NAME"))) = false /*default*/;


4) Done. Compile your project and utilize the measurements.
***********************************************************

You can adapt the tracefile name by specifying `VARA_TRACE_FILE` in the environment.

.. code-block:: console

    export VARA_TRACE_FILE=my_little_tracefile.json


Instrumentations
----------------

* `print`: Print entry/exit messages when entring a feature specific code
* `clock`: Add hw-clock based measurements that determine the time spent in a feature
* `trace_event`: Add trace event markers that generate catapult (trace event format) files
* `instr_verify`: Add verifier instrumentation that checks if feature regions are correctly opened/closed
* `usdt`: Add feature specific usdt probes
