#!/bin/bash

nosetests $(dirname $0)/unit/*.py
#nosetests --nocapture $(dirname $0)/functional/*.py
nosetests $(dirname $0)/functional/*.py
nosetests $(dirname $0)/berlinium/*_test.py
nosetests $(dirname $0)/apps/perovskite_tilting/*.py
