#!/usr/bin/python

import threading
import SocketServer
import alsaaudio
import socket
import re
import sys
import struct
import os
import numpy
import select
import traceback
import argparse
import pexpect

CMDLEN = 1024 # should always fit
BUFFER_SIZE = 1024 # from dspserver
PERIOD = 1024 # BUFFER_SIZE*4/N, N=4
TXLEN = 500 # from dspserver
PTXLEN = 1024 # for predsp

SAMPLERATE = 48000 # default for I/Q input
RIGCTL = "rigctl -m 229 -s 38400 -r "

class SharedData(object):
	def __init__(self, predsp=False):
		self.mutex = threading.Lock()
		self.clients = {}
		self.receivers = {}
		self.predsp = predsp
		self.exit = False

	def acquire(self):
		self.mutex.acquire()

	def release(self):
		self.mutex.release()

class ConnectedClient(object):
	def __init__(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8*1024**2)
		self.receiver = -1
		self.port = -1

class KX3(object):
	def __init__(self, ad=None, cd=None, swapiq=None):
		self.ad = ad
		rig_freq = pexpect.run(RIGCTL+cd+" f")
		self.rigctl = pexpect.spawn(RIGCTL+cd)
		self.rigctl.timeout = 2.5
		self.swapiq = swapiq
		self.set_freq(rig_freq)

	def set_freq(self, freq):
	    self.rigctl.sendline("F " + str(freq))
	    self.rigctl.expect("Rig command: ")

	def get_pcm(self, period=1024):
		pcm = alsaaudio.PCM(type=alsaaudio.PCM_CAPTURE, mode=alsaaudio.PCM_NORMAL, card=self.ad)
		pcm.setchannels(2)
		pcm.setrate(SAMPLERATE)
		pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
		pcm.setperiodsize(period)
		return pcm

class Listener(SocketServer.ThreadingTCPServer):
	def __init__(self, server_address, RequestHandlerClass, shared):
		SocketServer.ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
		self.shared = shared

class ListenerHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		caddr = self.client_address
		shared = self.server.shared
		shared.acquire()
		shared.clients[caddr] = ConnectedClient()
		shared.release()
		while 1:
			while not select.select([self.request], [], [], 1)[0]:
				if shared.exit:
					self.request.close()
					return
			try:
				data = self.request.recv(CMDLEN)
			except:
				break
			if not data:
				break
			m = re.search('^attach (\d+)', data, re.M)
			if m:
				shared.acquire()
				if shared.clients[caddr].receiver!=-1:
					shared.release()
					self.request.sendall('Error: Client is already attached to receiver')
					continue
				if int(m.group(1)) not in shared.receivers.keys():
					shared.release()
					self.request.sendall('Error: Invalid Receiver')
					continue
				if int(m.group(1)) in [shared.clients[i].receiver for i in shared.clients.keys()]:
					shared.release()
					self.request.sendall('Error: Receiver in use')
					continue
				shared.clients[caddr].receiver = int(m.group(1))
				shared.release()
				self.request.sendall('OK '+str(SAMPLERATE))
				continue
			m = re.search('^detach (\d+)', data, re.M)
			if m:
				shared.acquire()
				if shared.clients[caddr].receiver==-1:
					shared.release()
					self.request.sendall('Error: Client is not attached to receiver')
					continue
				if shared.clients[caddr].receiver!=int(m.group(1)):
					shared.release()
					self.request.sendall('Error: Invalid Receiver')
					continue
				shared.clients[caddr].receiver = -1
				shared.clients[caddr].port = -1
				shared.release()
				self.request.sendall('OK '+str(SAMPLERATE))
			m = re.search('^frequency ([0-9.,e+-]+)', data, re.M)
			if m:
				shared.acquire()
				if shared.clients[caddr].receiver==-1:
					shared.release()
					self.request.sendall('Error: Client is not attached to receiver')
					continue
				idx = shared.clients[caddr].receiver
				kx3 = shared.receivers[idx]
				shared.release()
				try:
					freq = int(m.group(1))
					kx3.set_freq(freq)
				except:
					self.request.sendall('Error: Invalid frequency')
					continue
				self.request.sendall('OK')
				continue
			m = re.search('^start (iq|bandscope) (\d+)', data, re.M)
			if m:
				shared.acquire()
				if shared.clients[caddr].receiver==-1:
					shared.release()
					self.request.sendall('Error: Client is not attached to receiver')
					continue
				if m.group(1)=='iq':
					shared.clients[caddr].port = int(m.group(2))
				shared.release()
				self.request.sendall('OK')
				continue
			m = re.search('^stop (iq|bandscope)', data, re.M)
			if m:
				shared.acquire()
				if shared.clients[caddr].receiver==-1:
					shared.release()
					self.request.sendall('Error: Client is not attached to receiver')
					continue
				if m.group(1)=='iq':
					if shared.clients[caddr].port==-1:
						shared.release()
						self.request.sendall('Error: Client is not started')
						continue
					shared.clients[caddr].port = -1
				shared.release()
				self.request.sendall('OK')
				continue
			## Don't crash QtRadio by telling it that this is a KX3! 
			#m = re.search('^hardware\?', data, re.M)
			#if m:
			#	self.request.sendall('OK KX3')
			#	continue
			self.request.sendall('Error: Invalid Command')
		shared.acquire()
		shared.clients.pop(caddr)
		shared.release()

def run_listener(c, h, p):
	try:
		server = Listener((h, p), ListenerHandler, c)
	except:
		c.exit = True
		traceback.print_exc()
		return
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.shutdown()
		server.server_close()
		c.exit = True
		try:
			c.release()
		except:
			pass

def kx3_io(shared, kx3, idx):
	shared.acquire()
	if idx in shared.receivers.keys():
		shared.release()
		raise IOError, 'Receiver with index %d already connected' % (idx)
	shared.receivers[idx] = kx3
	predsp = shared.predsp
	shared.release()
	pcm = kx3.get_pcm(PERIOD)
	seq = 0L
	while 1:
		length, audio = pcm.read()
		if length==-32:
			sys.stderr.write('Overrun\n')
		if length<1:
			continue
		rcv = []
		shared.acquire()
		for caddr in shared.clients.keys():
			if shared.clients[caddr].receiver==idx and shared.clients[caddr].port!=-1:
				rcv.append((shared.clients[caddr].socket, (caddr[0], shared.clients[caddr].port)))
		shared.release()
		if shared.exit:
			return
		if predsp:
			for j in xrange(0, (len(audio)+PTXLEN-1)/(PTXLEN)):
				for k in rcv:
					snd = struct.pack('<I', seq&0xFFFFFFFF)
					k[0].sendto(snd+audio[j*PTXLEN:j*PTXLEN+min(len(audio)-j*PTXLEN, PTXLEN)], (k[1][0], k[1][1]+500))
		else:
			naudio = numpy.fromstring(audio, dtype="<h")/numpy.float32(32767.0)
			naudio.resize(len(naudio)/(BUFFER_SIZE*2), BUFFER_SIZE*2)
			for i in naudio:
				if kx3.swapiq:
					txdata = i[::2].tostring() + i[1::2].tostring()
				else:
					txdata = i[1::2].tostring() + i[::2].tostring()
				for j in xrange(0, (len(txdata)+TXLEN-1)/(TXLEN)):
					for k in rcv:
						snd = struct.pack('<IIHH', seq&0xFFFFFFFF, (seq>>32)&0xFFFFFFFF, j*TXLEN, min(len(txdata)-j*TXLEN, TXLEN))
						k[0].sendto(snd+txdata[j*TXLEN:j*TXLEN+min(len(txdata)-j*TXLEN, TXLEN)], k[1])
				seq += 1

def create_kx3_thread(clients, kx3, idx=0):
	t = threading.Thread(target=kx3_io, args=(clients, kx3, idx))
	t.start()
	return t

# main
parser = argparse.ArgumentParser(description='kx3-server.py')
parser.add_argument('serial_device', help = 'the serial device that the KX3 is connected on i.e. /dev/ttyUSB0')
parser.add_argument('audio_device', help = 'the audio device that the KX3 is connected on i.e. hw:0')
parser.add_argument('-r', '--samplerate', type=int, default=48000, help = 'the sample rate for the I/Q data, i.e spectrum bandwidth')
parser.add_argument('-s', '--swapiq', action='store_true', default=False, help = 'Swap the I and Q inputs, reversing the spectrum')
parser.add_argument('-p', '--predsp', action='store_true', default=False, help = 'Offload some processing to an instance of predsp.py')
parser.add_argument('-a', '--ipaddr', default='0.0.0.0', help = 'The server\'s IPv4 address to bind to. Default is all addresses, '+
                                                                'i.e. 0.0.0.0 (alias addresses can be used)')

args = parser.parse_args()
SAMPLERATE = args.samplerate

if args.swapiq:
    print "swapiq is " + str(args.swapiq)
if args.predsp:
    print "predsp is " + str(args.predsp)

shared = SharedData(args.predsp)

try:
    kx3 = KX3(cd=args.serial_device, ad=args.audio_device, swapiq=args.swapiq )
except IOError:
	sys.stderr.write('KX3 not found\n')
	sys.exit(0)
	
ft = create_kx3_thread(shared, kx3, 0)
run_listener(shared, args.ipaddr, 11000)

