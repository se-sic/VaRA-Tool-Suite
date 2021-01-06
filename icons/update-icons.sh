#!/bin/sh

script=$(readlink -f "$0")
scriptpath=$(dirname "${script}")

pyrcc5 icons.qrc -o "${scriptpath}"/../varats/gui/icons_rc.py
