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
 - Switch to native KX3 control messages, avoiding use of hamlib/rigctl

Basic usage:
 - run kx3-server.py -s -r 192000 /dev/ttyUSB0 hw:0  (or similar)
 - run dspserver --soundcard U7_KX3 --lo 0 (or similar)
 - run QtRadio and connect to the dspserver

Usage: kx3-server.py [-h] [-r SAMPLERATE] [-s] [-p] [-a IPADDR] serial_device audio_device

kx3-server.py

positional arguments:
 - serial_device         the serial device that the KX3 is connected on i.e.
                        /dev/ttyUSB0
 - audio_device          the audio device that the KX3 is connected on i.e.
                        hw:0

optional arguments:
 - -h, --help            show this help message and exit
 - -r SAMPLERATE, --samplerate SAMPLERATE
                        the sample rate for the I/Q data, i.e spectrum
                        bandwidth
 - -s, --swapiq          Swap the I and Q inputs, reversing the spectrum
 - -p, --predsp          Offload some processing to an instance of predsp.py
 - -a IPADDR, --ipaddr IPADDR
                        The server's IPv4 address to bind to. Default is all addresses,
                        i.e. 0.0.0.0 (alias addresses can be used)


Predsp:
If you want to run kx3-server.py on embedded hardware (like BeagleBone Black),
you probably would want to move all data preprocessing (eg. conversion from ints to floats)
to host running dspserver. For that purpose there is a script called predsp.py. Usage:
 - on embedded host run 'kx3-server.py -p'
 - on more capable host run 'predsp.py' and 'dspserver --server <embedded host ip>'
 - run QtRadio or another client and point it to dspserver's address

Notes:
 - Don't touch that dial! Changing the KX3's frequency by any direct means should be avoided.
 If you nudge the tuning knob, set it back where it was.  The rig should be tuned 9kHz below the
selected VFO for QtRadios primary receiver.
 - Make sure the frequency readout on the KX3's display shows a resolution down to 1Hz, otherwise
a frequency mismatch might occur when the primary receiver in QtRadio changes frequency, as the KX3
seems to round the requested frequency to the displayed resolution. 
 - You must ensure that the KX3's filter is set to FL1 and the RX SHFT is off (set to normal), otherwise there will be a frequency mismatch in QtRadio.  Once we switch to native KX3 commands, we can probably compensate for this.
 - By default a +9kHz offset is used for the primary receiver (VFO A or B) and a variable offset for 
the sub-receiver.  If you establish an XIT offset of +9kHz on the KX3 and set the KX3's mode to match the 
listening mode in QtRadio, you can probably make QSOs using QtRadio as the receiver. However, an easier
solution is to invoke dspserver with the "--lo 0" option.  This gives the main receiver in QtRadio a 0Hz
offset, which is very convenient, but might not any good for listening to AM without using the sub-receiver (YMMV).
 - To use fldigi with QtRadio and the KX3, with Pulse Audio Volume Control (pavucontrol) you can have
fldigi listen to the output of QtRadio and transmit to the soundcard interface to your KX3 directly.
 - You can use wsjtx with QtRadio and the KX3 using the same technique as described above for fldigi. Note 
that the split feature doesn't work with wsjtx and QtRadio as QtRadio knows nothing about the KX3's
transmitter.  The split feature isn't really useful, as the KX3 isn't thought to be stable enough for JT9
transmission anyway.  I have made JT-65 contacts this way though.
 - Configure the KX3 to use a baud rate of 38400 for CAT control.
 - Pull request #31 in ghpsdr3-alex adds roughly calibrated s-meter and power spectrum scaling for a KX3 used with an Asus Xonar U7 soundcard  to dsperver (https://github.com/alexlee188/ghpsdr3-alex/pull/31).


