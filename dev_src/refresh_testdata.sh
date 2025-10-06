#!/bin/bash
for v in v2 v4; do
    DIR_DATA=/fast/peijinz/agile_proc/testdata_$v
    DIR_DATA_SRC=/fast/peijinz/agile_proc/testdata_$v.tar # tar file of the testdata
    DIR_OUTPUT=/fast/peijinz/agile_proc/

    # remove the directory
    rm -rf $DIR_DATA
    # untar the testdata
    tar -xvf $DIR_DATA_SRC -C $DIR_OUTPUT
done