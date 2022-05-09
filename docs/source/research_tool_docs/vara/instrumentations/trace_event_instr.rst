Trace-Event Format (``trace_event``)
====================================

VaRA can automatically insert TEF instrumentation markers for measuring the time that's spent within a region.
The instrumention measures the time using ``std::chrono`` in miliseconds, outputting a trace file in the end.
The file contains `start` events, when a region is entered, and `end` events, when a region is left.

Good tools for viewing the generated trace file are the newly developed trace viewer `perfetto <https://ui.perfetto.dev/>`_ or the chrome's internal trace viewer, which can be accessed by typing `about:tracing` into the search box.

For more information, see the format definition `here <https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview>`_.
