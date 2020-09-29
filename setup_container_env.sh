#!/usr/bin/sh

# Persistent storage for container images
export BB_CONTAINER_ROOT=~/uni/vara/benchbuild/.bb_containers/lib
# Temporary runtime data for container images
export BB_CONTAINER_RUNROOT=~/uni/vara/benchbuild/.bb_containers/run
# The container runtime to use.
export BB_CONTAINER_RUNTIME=/usr/bin/crun
# Benchbuild's source directory to do a source-based install.
export BB_CONTAINER_SOURCE=~/uni/benchbuild

alias bbuildah='buildah --root $BB_CONTAINER_ROOT --runroot $BB_CONTAINER_RUNROOT'
alias bpodman='podman --root $BB_CONTAINER_ROOT --runroot $BB_CONTAINER_RUNROOT'
