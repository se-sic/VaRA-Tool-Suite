#!/bin/bash

if [ ! -d "extern/benchbuild/benchbuild" ]; then
  git submodule init extern/benchbuild
  git submodule update extern/benchbuild
fi

if [ ! -L "extern/benchbuild/benchbuild/experiments/vara-experiments" ]; then
  ln -s ../../../../benchbuild/experiments extern/benchbuild/benchbuild/experiments/vara-experiments
fi
if [ ! -L "extern/benchbuild/benchbuild/projects/vara-projects" ]; then
  ln -s ../../../../benchbuild/projects extern/benchbuild/benchbuild/projects/vara-projects
fi
