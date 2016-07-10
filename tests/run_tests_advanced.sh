#!/bin/bash

nosetests $(dirname $0)/berlinium/*_test.py
nosetests $(dirname $0)/apps/perovskite_tilting/*.py
