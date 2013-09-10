Tilde
=====

Tilde (aka wwwtilda or ~) is an intelligent data organizer for cheminformatics and computational materials science.

Warning
-------

This is NOT a public release, rather a proof-of-concept code summary for internal needs.
It is not fully tested and may work unstable.
End users are HIGHLY DISCOURAGED of using this code.
However the user data are sacred and will never be affected.

Usage
-----

Please, avoid spaces and non-latin characters in the application folder name.
The main script is called "tilde.bat" (for Windows) and "tilde.sh" (for Unix).
All user commands should be executed through this main script:
To use command-line interface run main script with a parameter (e.g. "--help").
To start graphical interface run main script without parameters.
To terminate graphical interface on Windows close the DOS box, on Unix hit Ctrl+C.

Prerequisites
-------------

On Windows no additional installations are required.
On Unix/Mac you should have Python (at least of version 2.6), numerical modules (Numpy) and sqlite3 python module pre-installed.
Typically, this is the case on modern Unix PCs (console command "python -c 'import numpy, sqlite3'" should produce no errors).

License and distribution
------------------------

This program has MIT-license.
This means everybody is welcomed to use it for own needs or modify and adopt its source code.

Feedback and bugreports
-----------------------

Your feedback and bugreports are very anticipated at eb@tilde.pro or in GitHub http://github.com/jam31/wwwtilda

Summary
-------

* Webpage: http://wwwtilda.googlecode.com
* Maintainer: Evgeny Blokhin (eb@tilde.pro)
* Timestamp: 10/09/2013
