#!/bin/bash

nosetests $(dirname $0)/unit/*.py
nosetests $(dirname $0)/functional/*.py
