Tilde
=====

Tilde (aka wwwtilda or ~) is a data organizer for computational materials science.

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
All user commands are executed through this main script:
To use command-line interface (CLI), run main script with a parameter (e.g. "-h" or "-help").
To start graphical interface (GUI), run main script without parameters.
To terminate GUI on Windows, close the DOS box, on Unix hit Ctrl+C.
On Unix GUI may also run in background mode ("nohup tilde.sh &").
Adding data is possible using both CLI and GUI:
Using CLI: append "-a" option to the folder name.
Using GUI: click "add data" button at the top left corner of the program window.
Avoid using GUI on large folders with data (more than several gigabytes), as CLI is much faster in this case.

Prerequisites
-------------

On Windows no additional installations are required.
On Unix/Mac you should have Python (at least of version 2.6), numerical modules (Numpy) and sqlite3 python module pre-installed.
Typically, this is the case on modern Unix PCs (console command "python -c 'import numpy, sqlite3'" should produce no errors).
Note, that Python 3 was never tested.

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
* Timestamp: 30/09/2013
