#!/bin/bash
# Tilde project: entry point for Unix (MacOS) environment
# See http://tilde.pro

/usr/bin/env python $(dirname $0)/core/cli.py "$@"
