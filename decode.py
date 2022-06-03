#!/usr/bin/env python3

""" @package docstring
Manchester encoder

Encodes a file using the manchester encoding and outputs it as audio file
See https://www.youtube.com/watch?v=8BhjXqw9MqI&list=PLowKtXNTBypH19whXTVoG3oKSuOcw_XeW&index=3
and following videos by awesome Ben Eater
Very slow and inefficient implementation, meant only to be clear and didactic

@author Daniele Verducci <daniele.verducci@ichibi.eu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import logging
import wave
import struct

NAME = 'manchester-decoder'
VERSION = '0.1'
DESCRIPTION = 'Decodes a file using the manchester encoding'

FRAME_DELIMITER = 129 # (1, 0, 0, 0, 0, 0, 0, 1)
PREAMBLE_DURATION = 128
ZERO_POINT = 0 # The 0 value: values less than this are considered 0, more than this 1

class Main:

	def __init__(self):
		self._log = logging.getLogger('main')
		self.clockDuration = 0

	def run(self, inputFile, outputFile):
		# Open input audio file
		self.audioSource = wave.open(inputFile,'r')

		try:
			self.syncWithClock()
			self._log.info("Sync: clock duration is {}".format(self.clockDuration))
			#self.waitForStart()
			#self._log.info("Found start of data")
		except ValueError as e:
			self._log.error("Ran out of input data before completing initialization!")

		#self.decodeFile()

		self.audioSource.close()

	def syncWithClock(self):
		# Uses the preamble to obtain the clock duration
		i = 0
		while True:
			(duration, value) = self.readRawBit()

			print(duration, value)
			
			if i < PREAMBLE_DURATION/4:
				# First cycles are used to extimate clock duration
				self.clockDuration = self.clockDuration + duration / 2
				i = i + 1
		# We are now synced with clock. Add a 25% "slack" to make following samples at 
		# 1/4 and 3/4 to clock cycle: remember that every cycle has 2 values: 01 if the
		# encoded bit was 1 and 10 if it was 0
		for x in range(0, int(self.clockDuration / 4)):
			self.readRawBit()

	def waitForStart(self):
		# After the clock has been extimated, continue reading and wait for first delimiter
		lastByte = 0
		while True:
			value = decodeBit()

			# Shift the byte to left and add the read bit in the least significant position
			lastByte = lastByte << 1
			if value:
				lastByte = lastByte + 1

			if lastByte == FRAME_DELIMITER:
				# Found frame delimiter! We are in sync! YAY!
				return
			
	#def decodeFile():
		# From the bit after the FRAME_DELIMITER on, there is the real data. Decode and write to file

		#try:

		#except ValueError as e:
			# Completed reading file
			
	def readRawBit(self):
		# Reads a raw bit. Returns the duration of that bit and the value.
		duration = 0
		prev = None
		while True:
			frame = self.audioSource.readframes(1)
			if not frame:
				raise ValueError('No more data to read')

			v = int(struct.unpack('<h', frame)[0]) > ZERO_POINT
			
			if prev is None:
				prev = v
			else:
				# Detect zero crossing
				if prev < ZERO_POINT and v > ZERO_POINT:
					break
				if prev > ZERO_POINT and v < ZERO_POINT:
					break

				prev = v
				duration = duration + 1

		return (duration, prev > ZERO_POINT)

	def decodeBit(self):
		# Reads and decodes 2 raw bits into 1 decoded bit. 01 (raising) = 1, 10 (falling) = 0
		# Works only once clock is synced
		# The bits are read at 1/4 and 3/4 of clock cycle
		firstHalfFrame = self.audioSource.readframes((self.clockDuration/2) - 1)
		if not firstHalfFrame:
			raise ValueError('No more data to read')

		secondHalfFrame = self.audioSource.readframes(1)
		if not secondHalfFrame:
			raise ValueError('No more data to read')

		firstHalfRawBit = int(struct.unpack('<h', firstHalfFrame)[0]) > ZERO_POINT
		secondHalfRawBit = int(struct.unpack('<h', secondHalfFrame)[0]) > ZERO_POINT

		if not firstHalfRawBit and secondHalfRawBit:
			return True
		elif firstHalfRawBit and not secondHalfRawBit:
			return True
		else:
			# Lost sync!!!
			raise Exception()







		


if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(
		prog = NAME + '.py',
		description = NAME + ' ' + VERSION + '\n' + DESCRIPTION,
		formatter_class = argparse.RawTextHelpFormatter
	)
	parser.add_argument('inputFile', help="audio file to decode (in wav format)")
	parser.add_argument('outputFile', help="decoded file to write")
	parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
	args = parser.parse_args()

	if args.verbose:
		logging.basicConfig(level=logging.INFO)
	else:
		logging.basicConfig()

	main = Main()
	main.run(args.inputFile, args.outputFile)

	sys.exit(0)
