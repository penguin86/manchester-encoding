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


NAME = 'manchester-encoder'
VERSION = '0.1'
DESCRIPTION = 'Encodes a file using the manchester encoding and outputs it as audio file'

FRAME_DELIMITER = 129 # (1, 0, 0, 0, 0, 0, 0, 1)



class Main:

	def __init__(self):
		self._log = logging.getLogger('main')

	def run(self, inputFile, outputFile, clock):
		# Open output file

		# Read input file
		bytesToEncode = []
		with open(inputFile, 'rb') as f:
			position = 0
			while 1:
				byte = f.read(1)
				if not byte:
					# Finished reading file
					# Terminate with delimiter and exit
					self.encodeByte(FRAME_DELIMITER)
					break
				byte = byte[0]

				# Every 64 bytes, outputs a frame delimiter: 01111110
				# This is used by receiver to syncronize to the start of a byte
				if position % 64 == 0:
					self.encodeByte(FRAME_DELIMITER)
				position = position + 1

				# Encode byte
				self.encodeByte(byte)
		
		self._log.info('Completed')

	def encodeByte(self, byte):
		# Encodes a byte with the Mancester Encoding
		# Note that the byte is read from the most important to the least important bit
		# Es: 10000010 is not 130, but 65
		consecutiveOnes = 0

		for x in range(8):
			# Shift byte and take last bit (with bitwise AND)
			lastBit = ( byte >> x ) & 1

			# Write bit
			self.encodeBit(lastBit)

			# If we have 5 consecutive "1", add a 0 after, to avoid being interpreted as a frame delimiter
			if lastBit:
				consecutiveOnes = consecutiveOnes + 1
			else:
				consecutiveOnes = 0
			
			if consecutiveOnes == 5:
				self.encodeBit(0)
				consecutiveOnes = 0

	def outputPreamble(self):
		# Outputs the preable: a sequence of 64 "1" and "0" used to facilitate the receiver
		# syncronizing on our clock. The sequence starts with 1 and ends with 0
		for x in range(64):
			self.encode(x % 2 == 0)

	def encodeBit(self, bit):
		# Encodes a single bit in a pair of bits to be written on the media.
		# The "1" is encoded as a transition from 0 to 1 (01) while the "0" is endoded as a 
		# transition from 1 to 0 (10)
		if bit:
			self.out(0)
			self.out(1)
		else:
			self.out(1)
			self.out(0)

	def out(self, encodedBit):
		# Write already encoded bit on the media
		if encodedBit:
			print('―', end='')
		else:
			print('_', end='')


if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(
		prog = NAME + '.py',
		description = NAME + ' ' + VERSION + '\n' + DESCRIPTION,
		formatter_class = argparse.RawTextHelpFormatter
	)
	parser.add_argument('inputFile', help="file to encode")
	parser.add_argument('outputFile', help="audio file to write")
	parser.add_argument('clock', help="clock speed, in hz")
	parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
	args = parser.parse_args()

	if args.verbose:
		logging.basicConfig(level=logging.INFO)
	else:
		logging.basicConfig()

	main = Main()
	main.run(args.inputFile, args.outputFile, args.clock)

	sys.exit(0)
