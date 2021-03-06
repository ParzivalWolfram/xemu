"""

xemu v0.312b, by Parzival Wolfram <parzivalwolfram@gmail.com>
emulated CPU by ccc814p (https://github.com/ccc814p)
this code is under the MIT license
load a ROM from "rom.bin" next to it by default, can specify once ran
thanks to netikras (https://github.com/netikras), SortOfTested (https://devrant.com/users/SortOfTested)
and sbiewald (https://github.com/varbin) for optimization help

"""
from time import time

class StateVars(object): #supposedly this is more efficient
        #important stuff
        ROM = ["00"]*16 #0-$ff values, 0-15 addresses, with rules, map indirect via P and PC and not actual address lines
        RAM = [0]*14 #0-15 values, but $E and $F are I/O for...
        inputIO = 0 #0-15, but input from... keyboard or w/e. Located at $F.
        outputIO = 0 #0-15, but outputs to... screen or w/e. Located at $E.
        outputNew = 0 #Emulator-only flag for internal use, not to be implemented in a real CPU unless necessary (it probably will be)
        
        #registers
        A = 0 #A register of the ALU. Technically, the ALU stuff will be hardware-backed if you have an x86 FPU!
        B = 0 #B register of the ALU.
        O = 0 #Output, or O, register of the ALU.
        PC = 0 #Program Counter, current address in ROM.
        P = 0 #Program register, this is the 8-bit contents of byte at PC but is processed in upper/lower halves. Bits 0-3 are processed first, bits 4-7 are dropped if it's a 1-nybble op or taken as the second nybble for 2-nybble things.
        BRK = 0 #Emulator register, not present on a "real" x04, for internal use only
        silent = False #used for internal benchmark and silent mode
        
        #sliding screen for characters, emulator-only, real screen (or other output object) may differ if one of these is ever made
        charBuffer = [" "]*32
        outputString = " "*32
        def __init__(self,ROM=["00"]*16,RAM=[0]*14,inputIO=0,outputIO=0,outputNew=0,A=0,B=0,O=0,PC=0,P=0,BRK=0,silent=False,charBuffer=[" "]*32,outputString=" "*32):
                self.ROM = ROM
                self.RAM = RAM
                self.inputIO = inputIO
                self.outputIO = outputIO
                self.outputNew = outputNew
                self.A = A
                self.B = B
                self.O = O
                self.PC = PC
                self.P = P
                self.BRK = BRK
                self.silent = silent
                self.charBuffer = charBuffer
                self.outputString = outputString
def initVars(init=False): #for use in the command processor and on init
        global currentState
        if init:
                return StateVars()
        else:
                return StateVars(ROM=currentState.ROM)

global currentState
currentState = initVars(True)

#4-bit charmap for emulated screen
inputdict = {" ":0,"l":1,"o":2,"r":3,"h":4,"d":5,"i":6,"n":7,"m":8,"g":9,"a":10,"b":11,"c":12,"f":13,"e":14,"t":15} #Mini-ASCII input dict
outputdict = {0:" ",1:"L",2:"O",3:"R",4:"H",5:"D",6:"I",7:"N",8:"M",9:"G",10:"A",11:"B",12:"C",13:"F",14:"E",15:"T"} #Mini-ASCII output dict

def romloader(romName="rom.bin"): #improved romloader: still shit, just now it works properly
        global currentState
        from binascii import hexlify #yup, really. fuck it.
        ROM_in = open(romName,"rb")
        ROM_data = str(hexlify(ROM_in.read())).strip("b'").strip("'") #make hex string and strip py3's surrounding garbage off
        ROM_in.close()
        del ROM_in
        ROM_data = [ROM_data[i:i+2] for i in range(0, len(ROM_data), 2)] #creates hex bytes in array
        transferLoop = 0
        while transferLoop < 16 and transferLoop < len(ROM_data): #a far better way than whatever the fuck i tried to do the first time
                currentState.ROM[transferLoop] = ROM_data[transferLoop]
                transferLoop += 1
        del ROM_data
        del transferLoop
        del hexlify #does this even work?
        
#set up easy opcode decoding for later
def decodeUpperNybble(byteIn): #called first to see what opcode we have
        return int(str(byteIn)[0],16)
def decodeLowerNybble(byteIn): #may not even be called literally ever
        return int(str(byteIn)[1],16)

#really terrible meat of the emulated CPU
def doInstruction(byteIn):
        global currentState
        currentState.P = currentState.ROM[currentState.PC]
        upperNybble = decodeUpperNybble(byteIn)
        #welcome to "python doesn't have case statements"
        #hey, good news: py3.10 is gonna be exciting for that exact reason, expect most of this emulator to be updated when that's out
        if upperNybble == 0: #BRK: Break... kinda. Halts execution permanently
                if not currentState.silent:
                        print("DEBUG: BRK")
                currentState.BRK = 1
                return "" #you'll see this a lot, we return an empty string unless we are to jump, hacky but it works well so w/e
        elif upperNybble == 1: #ADD: Add. Adds A to B and outputs to O
                if not currentState.silent:
                        print("DEBUG: ADD")
                currentState.O=(currentState.A+currentState.B)%16
                return ""
        elif upperNybble == 2: #SUB: Subtract. Subtracts A from B and stores the output into O
                if not currentState.silent:
                        print("DEBUG: SUB")
                currentState.O=abs(currentState.A-currentState.B)%16
                return ""
        elif upperNybble == 3: #LAM: Load A from Memory, loads A from memory location determined by lower nybble
                target = decodeLowerNybble(byteIn)
                if not currentState.silent:
                        print("DEBUG: LAM "+str(target))
                if target == 15: #because nybbles 14 and 15 are actually I/O, we need to check that we're not grabbing those, because they're separate vars
                        currentState.A=currentState.inputIO
                elif target == 14:
                        currentState.A=currentState.outputIO
                else:
                        currentState.A=currentState.RAM[target]
                return ""
        elif upperNybble == 4: #LDA: Load A from immediate (lower nybble stored into A)
                if not currentState.silent:
                        print("DEBUG: LDA "+str(decodeLowerNybble(byteIn)))
                currentState.A=decodeLowerNybble(byteIn)
                return ""
        elif upperNybble == 5: #ZJP: Zero Jump. Only if A is 0, jump.
                if not currentState.silent:
                        print("DEBUG: ZJP "+str(decodeLowerNybble(byteIn)))
                if currentState.A==0:
                        return decodeLowerNybble(byteIn)
                else:
                        return ""
        elif upperNybble == 6: #LDB: Load B from immediate (lower nybble)
                if not currentState.silent:
                        print("DEBUG: LDB "+str(decodeLowerNybble(byteIn)))
                currentState.B=decodeLowerNybble(byteIn)
                return ""
        elif upperNybble == 7: #LBM: Load B from Memory, load A from memory nybble determined by lower nybble
                target = decodeLowerNybble(byteIn)
                if not currentState.silent:
                        print("DEBUG: LBM "+str(target))
                if target == 15:
                        currentState.B=currentState.inputIO
                elif target == 14:
                        currentState.B=currentState.outputIO
                else:
                        currentState.B=currentState.RAM[target]
                return ""
        elif upperNybble == 8: #JMP: Jump, jumps to address determined by lower nybble
                if not currentState.silent:
                        print("DEBUG: JMP "+str(decodeLowerNybble(byteIn)))
                return decodeLowerNybble(byteIn)
        elif upperNybble == 9: #SOM: Store O to Memory, writes O to a memory location determined by lower nybble.
                target = decodeLowerNybble(byteIn)
                if not currentState.silent:
                        print("DEBUG: SOM "+str(target))
                if target == 15:
                        currentState.inputIO=currentState.O
                elif target == 14:
                        currentState.outputIO=currentState.O
                        currentState.outputNew=1
                else:
                        currentState.RAM[target]=currentState.O
                return ""
        elif upperNybble == 10: #AND: Bitwise AND A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: AND")
                currentState.O=(currentState.A&currentState.B)%16
                return ""
        elif upperNybble == 11: #OR: Bitwise OR A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: OR")
                currentState.O=(currentState.A|currentState.B)%16
                return ""
        elif upperNybble == 12: #XOR: Bitwise XOR A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: XOR")
                currentState.O=(currentState.A^currentState.B)%16
                return ""
        elif upperNybble == 13: #NND: Bitwise NAND A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: NND")
                currentState.O=abs(~(currentState.A&currentState.B))%16 #this may not work like this out of the box, i may have to split it
                return ""
        elif upperNybble == 14: #NOR: Bitwise NOR A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: NOR")
                currentState.O=abs(~(currentState.A|currentState.B))%16
                return ""
        elif upperNybble == 15: #XNR: Bitwise XNOR A and B, store into O.
                if not currentState.silent:
                        print("DEBUG: XNR")
                currentState.O=abs(~(currentState.A^currentState.B))%16
                return ""
        else:
                print("!!!CRASH!!!: out of bounds opcode found! upperNybble="+str(upperNybble)+",lowerNybble="+str(lowerNybble)) #to catch any funky Python logic, since sometimes it forgets what if statements are
                exit(1)
#handle the emulated keyboard, which doesn't really have to be a keyboard, but we'll just use it as one here because it's easier
def inputHandler(charIn): #charset given working title of "Mini-ASCII"
        global currentState
        getresult = inputdict.get(charIn.lower())
        if getresult != None:
                currentState.inputIO = getresult
                return ""
        return "INVCHAR"

#handles the emulated screen, which can be anything, really, but here it's a 32-char shift screen
def outputHandler():
        global currentState
        if currentState.outputNew==1:
                getresult = outputdict.get(currentState.outputIO)
                if getresult == None:
                        print("!!!CRASH!!!: out of bounds value sent from CPU! outputIO="+str(currentState.outputIO))
                        exit(1)
                charBuffer.append(getresult)
                currentState.outputNew = 0
                del currentState.charBuffer[0]
        currentState.outputString = ""
        for i in currentState.charBuffer:
                currentState.outputString+=i
        return

#steps the emulator forward one cycle, has some emu logic as well
def doStep():
        global currentState
        resultCode = ""
        resultCode = doInstruction(currentState.ROM[currentState.PC]) #we gotta catch jump codes if they pop up, so trap return value
        if resultCode == "": #hacky jump code, but w/e
                currentState.PC+=1
        else:
                currentState.PC = resultCode
        currentState.PC=currentState.PC%16 #as PC can't be >15
        if not currentState.silent:
                print("DEBUG: PC=$"+str(hex(currentState.PC)[2:]).upper()+",ROM[PC]=$"+str(currentState.ROM[currentState.PC]).upper()+",A=$"+str(hex(currentState.A)[2:]).upper()+",B=$"+str(hex(currentState.B)[2:]).upper()+",O=$"+str(hex(currentState.O)[2:]).upper()+",BRK="+str(currentState.BRK)+",P="+str("{0:08b}").format(int(str(currentState.P),16))+",OUT=$"+str(hex(currentState.outputIO)[2:]).upper()+",IN=$"+str(hex(currentState.inputIO)[2:]).upper()+",OUT_NEW="+str(currentState.outputNew)) #i'm not sorry for this monster of a line
                print("DEBUG: RAM="+str(currentState.RAM))
                print("DEBUG: outputString="+currentState.outputString)
        currentState.inputIO = 0
        outputHandler()
        return

#the worst command processor ever, like actually this is so very bad, please refactor if possible
def commandprocessor(commandIn):
        global currentState
        if commandIn == "":
                commandfunc = "step" #this emulates legacy xemu "hold ENTER to step" functionality. Yes, xemu was that basic once. 
        else:
                commandparts = commandIn.split(" ") #split input into chunks to parse
                del commandIn #free a little RAM
                commandfunc = str(commandparts[0]).lower() #what are we to do?   
        if commandfunc == "write" or commandfunc == "poke": #Should write to a RAM location (or I/O, though those are only separate in the emulator)
                try: #check if we were told where to write to
                        commandwhere = commandparts[1]
                except:
                        return "ARGCOUNT" #nothing received
                try:
                        commandwhere = int(commandwhere) #is it in decimal?
                except:
                        try:
                                commandwhere = int(commandwhere,16) #or hex?
                                pass
                        except:
                                return "ARGTYPE 1" #it wasn't a supported number type
                try: #check for what we're to write
                        commandwhat = commandparts[2]
                except:
                        return "ARGCOUNT" #no write value received
                try:
                        commandwhat = int(commandwhat) #is it in decimal?
                except:
                        try:
                                commandwhat = int(commandwhat,16) #or hex?
                                pass
                        except:
                                return "ARGTYPE 2" #what the hell did you pass me?
                if commandwhere > 15 or commandwhere < 0: #bounds check
                        return "ARGVAL 1" #out of bounds
                if commandwhat > 15 or commandwhat < 0: #bounds check
                        return "ARGVAL 2" #out of bounds
                if commandwhere == 14: #handle I/O being split in the emulator
                        currentState.outputIO = commandwhat
                elif commandwhere == 15: #handle I/O being split in the emulator
                        currentState.inputIO = commandwhat
                else:
                        currentState.RAM[commandwhere] = commandwhat
                return ""
        elif commandfunc == "reset" or commandfunc == "reboot" or commandfunc == "restart": #restarts the emulated chip
                currentState = initVars()
                return ""
        elif commandfunc == "load": #loads new ROM, with or without reset, but it should reset by default
                try: #check for filename being present
                        commandfilename = commandparts[1]
                except:
                        return "ARGCOUNT" #we didn't get a filename
                try: #check if we have the optional preserve flag
                        commandpreserve = commandparts[2]
                except:
                        commandpreserve = None
                        pass
                try: #test for valid file and perms and such
                        tester12 = open(commandfilename)
                        tester12.close()
                        del tester12
                except:
                        return "IOERR"
                if commandpreserve == None: #if no "preserve" flag present
                        romloader(commandfilename)
                        currentState = initVars()
                        return ""
                elif commandpreserve == "preserve": #if preserve flag present
                        romloader(commandfilename)
                        return ""
                else:
                        return "ARGTYPE 2" #if we have trailing garbage that isn't the right flag, error
        elif commandfunc == "input": #types a key on the emulated keyboard for one cycle, though the clearing is in doStep()
                try: #did the user specify a character?
                        commandchar = commandparts[1]
                except:
                        return "ARGCOUNT" #no, error
                return inputHandler(commandchar)
        elif commandfunc == "step": #step one or more CPU cycles ahead
                try: #checking for optional count
                        commandcount = commandparts[1]
                except:
                        commandcount = None
                        pass
                if commandcount != None: #do we have an extra parameter?
                        try:
                                int(commandcount) #is it a number?
                        except:
                                return "ARGVAL 1" #no, return
                if currentState.BRK == 1:
                        print("Cannot step, BRK processed. Please RESET.") #since a BRK should halt the CPU
                else:
                        if commandcount == None: #if no second argument, just do one
                                doStep()
                        elif int(commandcount) < 1: #how the fuck do we step 0 times? or negative times?
                                return "ARGVAL 1"
                        else:
                                commandcount = int(commandcount) #it breaks if this isn't here and idk why
                                while commandcount != 0 and currentState.BRK != 1:
                                        doStep()
                                        commandcount -= 1
                return ""
        elif commandfunc == "run" or commandfunc == "go": #just go infinitely, may add some break support at some point
                if currentState.BRK == 1: #since BRK halts the CPU
                        print("Cannot run, BRK processed. Please RESET.")
                else:
                        while currentState.BRK != 1:
                                doStep()
                return ""
        elif commandfunc == "output" or commandfunc == "print" or commandfunc == "tell": #print the same info we do on each step
                print("DEBUG: PC=$"+str(hex(currentState.PC)[2:]).upper()+",ROM[PC]=$"+str(currentState.ROM[currentState.PC]).upper()+",A=$"+str(hex(currentState.A)[2:]).upper()+",B=$"+str(hex(currentState.B)[2:]).upper()+",O=$"+str(hex(currentState.O)[2:]).upper()+",BRK="+str(currentState.BRK)+",P="+str("{0:08b}").format(int(str(currentState.P),16))+",OUT=$"+str(hex(currentState.outputIO)[2:]).upper()+",IN=$"+str(hex(currentState.inputIO)[2:]).upper()+",OUT_NEW="+str(currentState.outputNew)) #i'm not sorry for this monster of a line
                print("DEBUG: RAM="+str(currentState.RAM))
                print("DEBUG: outputString="+currentState.outputString)
                return ""
        elif commandfunc == "quit" or commandfunc == "exit": #quit emulator
                return "QUIT"
        elif commandfunc == "help" or commandfunc == "what" or commandfunc == "?": #print list of commands, update string when a new one is added
        
        #remind me to rewrite this readably at some point 300 years from now
                print("Command processor help:\nWRITE/POKE <where> <what>: Writes to RAM or virtual I/O.\nRESET/REBOOT/RESTART: Reboots the emulated CPU.\nLOAD <filename> (preserve): Loads a ROM. If the \"preserve\" keyword is included, the emulated CPU won't be reset after load.\nINPUT <char>: Writes a character to the emulated CPU's Input I/O. Only valid Mini-ASCII is supported.\nSTEP (count): Steps forward one CPU cycle. If the \"count\" parameter is included, STEP that many cycles at once. (You can press or hold ENTER to quickly STEP.)\nRUN/GO: Run until BRK processed. Cannot be interrupted, so be careful of infinite loops!\nPRINT/TELL/OUTPUT: Prints debug information (like you get after a STEP.)\nSILENCE: Toggles silent mode (no automatic debug output after steps, no disassembly output, etc.)\nBENCHMARK/TEST/BENCH (count): By default, times how long 500,000 x04 cycles takes on your machine in silent mode. If the \"count\" parameter is included, will time that many cycles instead. (This resets the emulated x04!)\nQUIT: Quits the emulator.")
                return ""
        elif commandfunc == "silence": #makes the emulator shut the fuck up
                if currentState.silent == True:
                        currentState.silent = False
                else:
                        currentState.silent = True
                return ""
        elif commandfunc == "bench" or commandfunc == "benchmark" or commandfunc == "test":
                try: #checking for optional count
                        commandcount = commandparts[1]
                except:
                        commandcount = None
                        pass
                if commandcount != None: #do we have an extra parameter?
                        try:
                                commandcount = int(commandcount) #is it a number?
                        except:
                                return "ARGVAL 1" #no, return
                else:
                        commandcount = 500000
                backupState = currentState
                initVars() 
                currentState.ROM = ["10"]*16 #decent benchmark methinks
                start = time()
                counter = 0
                currentState.silent = True
                while counter != commandcount:
                        doStep()
                        counter += 1
                        #print(counter)
                        #print(commandcount)
                stop = time()
                print(str(commandcount)+" steps took "+str(stop-start)+" seconds.")
                currentState = backupState
                del counter
                del backupState
                del start
                del stop
                return ""
        else: #we have no command by that name
                return "COMMAND" #please try again



#this is all that's left of the main body of the original script.
try:
        romloader("rom.bin")
except:
        while True: #exception loops are stupid but sometimes it's all you got
                try:
                        romloader(input("Bad or missing ROM.BIN\nPlease specify a file to use.\nInput>"))
                except:
                        continue
                else:
                        break

commandresult = ""
commandIn = input("Enter a command to run. Use HELP for a list of commands.\nInput> ") #pre-seed the interpreter
while True: #loop the interpreter
        commandresult = commandprocessor(commandIn) #pass command string to interpreter logic body
        if commandresult != "" and commandresult != "QUIT": #did we error?
                print("ERROR: Command processor returned error: "+commandresult) #tell the user if we did
        if commandresult == "QUIT": #quit the routine
                break #just fall through, exit() spits out an error even if we try code 0
        commandIn = input("Enter a command to run.\nInput> ")
