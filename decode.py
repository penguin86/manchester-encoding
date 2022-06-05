#!/usr/bin/env python3

""" @package docstring
Manchester decoder

Decodes a file encoded with the manchester code
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

FRAME_DELIMITER = 126 # (01111110)
FRAME_DELIMITER_EVERY_BYTES = 64
PREAMBLE_DURATION = 512
# Values nearest to zero than this are not considered: set to more than noise, less than signal
AUDIO_MIN_VOLUME = 12288
# The 0 value: values less than this are considered 0, more than this 1. This should be
# auto-adjusting (to leave out the DC component, in hw one would use a transformer)
ZERO_POINT = 0

class Main:

	def __init__(self):
		self._log = logging.getLogger('main')
		self.clockDuration = 0

	def run(self, inputFile, outputFile):
		# Open input audio file
		self.audioSource = wave.open(inputFile,'r')

		# Open output file
		with open(outputFile,'wb') as outf:
			self.outputSink = outf

			try:
				self.syncWithClock()
				self._log.info("Found clock: clock duration is {}".format(self.clockDuration))
				self.waitForStart()
				self._log.info("Synced to first byte: start decoding actual data")
				self.decodeActualData()
			except ValueError as e:
				self._log.error("Ran out of input data before completing initialization!")

		self.audioSource.close()
		self.outputSink.close()

	def syncWithClock(self):
		# Uses the preamble to obtain the clock duration
		analyzedCycles = 0
		while True:
			(cycles, raising) = self.goToNextZeroCrossing(True)
			analyzedCycles = analyzedCycles + cycles
			self._log.debug("Found zero crossing after {}, raising: {}".format(cycles, raising))

			if analyzedCycles > PREAMBLE_DURATION * self.clockDuration / 4:
				# At this point we should have an idea of the clock duration, move on
				return

	def waitForStart(self):
		# After the clock has been extimated, continue reading and wait for first delimiter
		lastByte = 0
		while True:
			value = self.decodeBit()

			# Shift the byte to left
			lastByte = lastByte << 1
			# Truncate the length to 8 bits
			lastByte = lastByte & 255 # 0 11111111
			# Add the read bit in the least significant position
			if value:
				lastByte = lastByte + 1

			if lastByte == FRAME_DELIMITER:
				# Found frame delimiter! We are in sync! YAY!
				self._log.info("Found first frame delimiter")
				return

	def decodeActualData(self):
		# From the bit after the FRAME_DELIMITER on, there is the actual data. Decode at groups of 8 bytes and write to file
		position = 0 # We already consumed the first delimiter
		try:
			while True:
				expectFrameDelimiter = position > 0 and position % FRAME_DELIMITER_EVERY_BYTES == 0
				if expectFrameDelimiter:
					decodedByte = self.decodeByte(True)
					if decodedByte != FRAME_DELIMITER:
						raise ValueError('Expecting a frame delimiter, found {} at position {}'.format(decodedByte, position))
					self._log.debug('Found frame delimiter')

				decodedByte = self.decodeByte(False)
				try:
					self.outputSink.write(bytes([decodedByte]))
				except Exception as e:
					self._log.error(e)
				position = position + 1

		except ValueError as e:
			# Stream finished
			# If last byte isn't a frame delimiter, throw error
			self._log.info(e)

	def decodeByte(self, expectFrameDelimiter=False):
		# Decodes a byte (to be used _after_ the first frame delimiter was found)
		decodedByte = 0
		consecutiveOnes = 0
		for x in range(8):
			value = self.decodeBit()

			# Shift the byte to left
			decodedByte = decodedByte >> 1

			# Truncate the length to 8 bits
			decodedByte = decodedByte & 255 # 0 11111111
			# Add the read bit in the least significant position
			if value:
				decodedByte = decodedByte + 128 #10000000
				consecutiveOnes = consecutiveOnes + 1
			else:
				consecutiveOnes = 0

			if consecutiveOnes == 5 and not expectFrameDelimiter:
				# We found 5 1s: ignore next 0: has been added to avoid a real 01111110 byte to be interpreted as frame delimiter
				if self.decodeBit():
					# Should be 0!
					raise ValueError('Found xx0111111 while not expecting a delimiter!')
		return decodedByte


	def decodeBit(self, allowSilence = False):
		# Decodes a bit. Searches for the phase invertion at 75% to 125% of the clock cycle
		bitDuration = 0
		while True:
			(duration, raising) = self.goToNextZeroCrossing(False)
			bitDuration = bitDuration + duration
			if bitDuration < self.clockDuration * 0.75:
				# Ignore: half-cycle crossing due to two equal digits one near the other
				continue
			if bitDuration > self.clockDuration * 1.25:
				# Lost tracking!
				raise Exception("Lost tracking! No phase inversion found between {} and {} samples from the last one".format(self.clockDuration * 0.75, self.clockDuration * 1.25))

			# This is our phase inversion signal
			return raising



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

	def goToNextZeroCrossing(self, adjustClockDuration):
		# Find the next zero crossing and returns:
		# (cycles since last inversion, True if is raising, False if is falling)
		cyclesSinceLastInversion = 0
		prev = None
		while True:
			frame = self.audioSource.readframes(1)
			if not frame:
				raise ValueError('No more data to read')

			lvl = int(struct.unpack('<h', frame)[0])
			if lvl > AUDIO_MIN_VOLUME or lvl < -AUDIO_MIN_VOLUME:
				v = lvl > AUDIO_MIN_VOLUME
				if prev == None:
					prev = v
				if v != prev:
					# Zero-point crossing!
					if adjustClockDuration:
						self.clockDuration = (self.clockDuration + cyclesSinceLastInversion) / 2
					return (cyclesSinceLastInversion, v)

			# Count only cycles after first valid signal
			if prev != None:
				cyclesSinceLastInversion = cyclesSinceLastInversion + 1







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
	parser.add_argument('-d', '--debug', action='store_true', help="even more verbose output, for debug")
	args = parser.parse_args()

	if args.verbose:
		logging.basicConfig(level=logging.INFO)
	elif args.debug:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig()

	main = Main()
	main.run(args.inputFile, args.outputFile)

	sys.exit(0)
