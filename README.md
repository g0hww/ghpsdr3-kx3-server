ghpsdr3-kx3-server
=========================

A receive only KX3 server for ghpsdr3-alex, used with dspserver and QtRadio. 
This is based on ghpsdr3-fcdproplus-server: 
    https://github.com/bazuchan/ghpsdr3-fcdproplus-server

Python Dependencies are:
 - python-alsaaudio
 - python-numpy
 - python-expect
 
Requires:
 - Hamlib (calls rigctl)

Todo:
 - Not sure yet.

Basic usage:
 - run kx3-server.py (you may need the -s option to swap the I&Q channels
 - run dspserver
 - run QtRadio


Predsp:
If you want to run kx3-server.py on embedded hardware (like BeagleBone Black),
you probably would want to move all data preprocessing (eg. conversion from ints to floats)
to host running dspserver. For that purpose there is a script called predsp.py. Usage:
 - on embedded host run 'kx3-server.py -p'
 - on more capable host run 'predsp.py' and 'dspserver --server <embedded host ip>'
 - run QtRadio or another client and point it to dspserver's address


