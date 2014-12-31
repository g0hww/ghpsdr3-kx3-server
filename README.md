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
 - run kx3-server.py -s /dev/ttyUSB1 hw:0 -r 192000 (or similar)
 - run dspserver
 - run QtRadio

Usage: kx3-server.py [-h] [-r SAMPLERATE] [-s] [-p] serial_device audio_device

positional arguments:
  serial_device         the serial device that the KX3 is connected on i.e.
                        /dev/ttyUSB0
  audio_device          the audio device that the KX3 is connected on i.e.
                        /dev/ttyUSB0

optional arguments:
  -h, --help            show this help message and exit
  -r SAMPLERATE, --samplerate SAMPLERATE
                        the sample rate for the I/Q data, i.e spectrum
                        bandwidth
  -s, --swapiq          Swap the I and Q inputs, reversing the spectrum
  -p, --predsp          Offload some processing to an instance of predsp.py

Predsp:
If you want to run kx3-server.py on embedded hardware (like BeagleBone Black),
you probably would want to move all data preprocessing (eg. conversion from ints to floats)
to host running dspserver. For that purpose there is a script called predsp.py. Usage:
 - on embedded host run 'kx3-server.py -p'
 - on more capable host run 'predsp.py' and 'dspserver --server <embedded host ip>'
 - run QtRadio or another client and point it to dspserver's address


