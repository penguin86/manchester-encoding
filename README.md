# Manchester encoder/decoder

> This project was moved to [my private git server](https://git.ichibi.eu/penguin86/manchester-encoding) . This repository may not be up to date.
> This is a personal project, probably of little use for others, and I don't currently accept contributions on it. Anyway, feel free to contact me if you have any idea.

# What
[Manchester code](https://en.wikipedia.org/wiki/Manchester_code) is an encoding algorithm created originally to store data in the Manchester university's Mark 1 computer drum disk. Later used to store data on audio tape, in ethernet communications (base10), NFC etc.

This is my implementation of the specifications. There are two python scripts, one for encoding and one for decoding. The only audio format supported is WAV. This implementation tollerates a theoretical maximum phase shift (tape speed change) of 50%, and accepts silence and noise (at lower levels than the signal) before start and after end of signal.

# Why
I needed a simple and interoperable way to store data on my (Pat80)[https://github.com/penguin86/pat80] homebrew computer. Audio is a good idea because:
- it was used in a lot of home computers in the 80s
- it is standard: almost any phone or computer has a headphone exit that can be used to load applications on a home computer
- if one want the original feeling, audio tapes and audio recorders are still available in shops in 2022, while floppy disks are not

I wrote this code to teach myself the Manchester code and to prototype the whole process before trying to implement it with electronics and Z80 assembly. Therefore, the implementation is didactic: it works (very well), but is inefficient, and the code is written to be more understandable than efficient.

# How
## Encode a file to audio
Specify the input file, the audio output wav file and the clock.
The clock is the frequency used to encode the data. Faster clock = more data per second. Slower clock = more robust on bad quality tape (less high frequencies).
```
./encode.py input.txt encoded.wav 1000
```
Now you can write this file to your tape.

## Decode a wav file to the original file
Same of encoding, but clock speed is detected from the signal itself (if you play the signal, you can hear a first part used to extimate clock frequency).
```
./decode.py encoded.wav output.txt
```

## Troubleshooting
Use -v or -d flag to have printed on the terminal all the debug infos.
Use -h flag for more infos on script usage.

If the decoding script couldn't determine clock speed (or determines a wrong one), fiddle with the volume control on the tape recorder. If this doesn't work, you can adjust the minimum accepted signal volume changing the constant `AUDIO_MIN_VOLUME` in `decode.py` between 0 and 32768.
