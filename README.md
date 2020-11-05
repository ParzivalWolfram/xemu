# xemu
xemu: an emulator for a conceptual 4-bit CPU named "x04" by [ccc814p](https://github.com/ccc814p) written for Python 3. 100% accurate logic-wise, improvements are being made to UI for the most part aside from some code cleanup. Sports a command interpreter, and there is a help command if you get lost.

Requires binascii.hexlify(), time.time() and builtins. 

Requires a ROM to run (auto-loads "rom.bin" if placed next to it, will prompt for filename if not found) though these are all user-made thus far. A test ROM is provided.

Features:
- command interpreter and basic debug functions
- 100% accuracy for [ccc814p](https://github.com/ccc814p)'s x04 CPU
- keyboard and 32-character shifting screen emulation using [ccc814p](https://github.com/ccc814p)'s Mini-ASCII
- written somewhat-readably, so functions as something approaching documentation for the architecture
- written with [Starman0620](https://github.com/Starman0620)'s [xasm](https://github.com/Starman0620/xasm) assembler in mind
- a good example of how not to write code

Improvements are very welcome, the code is a mess.
