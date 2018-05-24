#!/usr/bin/env bash

LIB_DIRECTORY_BENCH=$(python3 -m site --user-site)"/benchbuild"
LIB_DIRECTORY_PROJ=$LIB_DIRECTORY_BENCH"/projects"
LIB_DIRECTORY_EXP=$LIB_DIRECTORY_BENCH"/experiments"
CUR_FOLDER_PROJ=$(pwd)"/varats/vara-projects"
CUR_FOLDER_EXP=$(pwd)"/varats/vara-experiments"
echo "Everything worked fine. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
ln -s $CUR_FOLDER_PROJ $LIB_DIRECTORY_PROJ
ln -s $CUR_FOLDER_EXP $LIB_DIRECTORY_EXP