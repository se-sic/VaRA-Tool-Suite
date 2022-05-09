Highlight Region
================

The idea behind a `HighlightRegion` is to highlight a specific code region by attaching additional customizable identifiers.
The boundary of the region is defined by ``___REGION_START`` and ``___REGION_END``, the region type ``__RT_High`` and the identifier afterwards.

For example, consider the code below where we want to highlight an important computation in the code.
To highlight the part where the answer to everything is computed, we put a ``___REGION_START`` marker before the call and a ``___REGION_END`` marker after we printed the answer.

.. code-block:: cpp

    int main() {
      std::cout << "Let's start working on some deep questions\n";

      ___REGION_START __RT_High "Important"
      auto Answer = getAnswerToEverything();
      std::cout << "Some important result: " << Answer << '\n';
      ___REGION_END __RT_High "Important"

      return 0;
    }


Then, to enable the automatic highlight region tracking of clang, we need to additionally add the C/CXX flag ``-fvara-handleRM=High``.
Afterwards, clang processes the region and annotates the internal compiler IR with our region information, enabling further analyses to recognize the code we highlighted.
