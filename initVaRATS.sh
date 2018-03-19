#!/bin/bash

if [ ! -d "extern/benchbuild/benchbuild" ]; then
  git submodule init extern/benchbuild
  git submodule update extern/benchbuild
fi

ln -sr benchbuild/experiments/ extern/benchbuild/benchbuild/experiments/vara-experiments
ln -sr benchbuild/projects/ extern/benchbuild/benchbuild/projects/vara-projects
