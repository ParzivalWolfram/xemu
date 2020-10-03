"""

xemu v0.249b, by Parzival Wolfram <parzivalwolfram@gmail.com>
emulated CPU by ccc814p (https://github.com/ccc814p)
this code is under the MIT license
load a ROM from "rom.bin" next to it by default, can specify once ran
thanks to netikras (https://github.com/netikras), SortOfTested (https://devrant.com/users/SortOfTested)
and sbiewald (https://github.com/varbin) for optimization help

"""

#important stuff
ROM = ["00"]*16 #0-$ff values, 0-15 addresses, with rules, map indirect via P and PC and not actual address lines
RAM = [0]*14 #0-15 values, but $E and $F are I/O for...
inputIO = 0 #0-15, but input from... keyboard or w/e. Located at $F.
outputIO = 0 #0-15, but outputs to... screen or w/e. Located at $E.
outputNew = 0 #Emulator-only flag for internal use, not to be implemented in a real CPU unless necessary (it probably will be)
inputdict = {" ":0,"l":1,"o":2,"r":3,"h":4,"d":5,"i":6,"n":7,"m":8,"g":9,"a":10,"b":11,"c":12,"f":13,"e":14,"t":15} #Mini-ASCII input dict
outputdict = {0:" ",1:"L",2:"O",3:"R",4:"H",5:"D",6:"I",7:"N",8:"M",9:"G",10:"A",11:"B",12:"C",13:"F",14:"E",15:"T"} #Mini-ASCII output dict

#registers
A = 0 #A register of the ALU. Technically, the ALU stuff will be hardware-backed if you have an x86 FPU!
B = 0 #B register of the ALU.
O = 0 #Output, or O, register of the ALU.
PC = 0 #Program Counter, current address in ROM.
P = 0 #Program register, this is 8-bit but is processed in upper/lower halves. Bits 0-3 are processed first, bits 4-7 are dropped if it's a 1-nybble op or taken as the second nybble for 2-nybble things.
BRK = 0 #Emulator register, not present on a "real" x04, for internal use only

#sliding screen for characters, emulator-only, real screen may differ if ever made
charbuffer = [" "]*32
outputString = " "*32

def initVars(): #for use in the command processor
        global inputIO #you will se this a lot and it makes me wanna die but python's stupid and i need to convert these to a class or some shit eventually
        global outputIO
        global outputNew
        global PC
        global ROM
        global RAM
        global A
        global B
        global O
        global P
        global BRK
        global charbuffer
        global outputString
        RAM = [0]*14
        inputIO = 0
        outputIO = 0
        outputNew = 0
        A = 0
        B = 0
        O = 0
        PC = 0
        P = 0
        BRK = 0
        charbuffer = [" "]*32
        outputString = " "*32

def romloader(romName="rom.bin"): #improved romloader: still shit, just now it works properly
        global ROM
        from binascii import hexlify #yup, really. fuck it.
        ROM_in = open(romName,"rb")
        ROM_data = str(hexlify(ROM_in.read())).strip("b'").strip("'") #make hex string and strip py3's surrounding garbage off
        ROM_in.close()
        del ROM_in #gives back approx. 1MB of RAM, might as well
        ROM_data = [ROM_data[i:i+2] for i in range(0, len(ROM_data), 2)] #creates hex bytes in array
        transferLoop = 0
        while transferLoop < 16 and transferLoop < len(ROM_data): #a far better way than whatever the fuck i tried to do the first time
                ROM[transferLoop] = ROM_data[transferLoop]
                transferLoop += 1
        del ROM_data #depending on original file's size, frees up to 16MB or so of RAM
        del transferLoop #frees like 4KB, but fuck it, why not?
        del hexlify #does this even work? it'd free up like 5MB if it does
        
#set up easy opcode decoding for later
def decodeUpperNybble(byteIn): #called first to see what opcode we have
        return int(str(byteIn)[0],16)
def decodeLowerNybble(byteIn): #may not even be called literally ever
        return int(str(byteIn)[1],16)

#really terrible meat of the emulated CPU
def doInstruction(byteIn):
        global A
        global B
        global O
        global PC
        global P
        global BRK
        global inputIO
        global outputIO
        global outputNew
        P = ROM[PC]
        upperNybble = decodeUpperNybble(byteIn)
        #welcome to "python doesn't have case statements"
        #hey, good news: py3.10 is gonna be exciting for that exact reason, expect most of this emulator to be updated when that's out
        if upperNybble == 0: #BRK: Break... kinda. Halts execution permanently
                print("DEBUG: BRK")
                BRK = 1
                return "" #you'll see this a lot, we return an empty string unless we are to jump, hacky but it works well so w/e
        elif upperNybble == 1: #ADD: Add. Adds A to B and outputs to O
                print("DEBUG: ADD")
                O=(A+B)%16
                return ""
        elif upperNybble == 2: #SUB: Subtract. Subtracts A from B and stores the output into O
                print("DEBUG: SUB")
                O=abs(A-B)%16
                return ""
        elif upperNybble == 3: #LAM: Load A from Memory, loads A from memory location determined by lower nybble
                target = decodeLowerNybble(byteIn)
                print("DEBUG: LAM "+str(target))
                if target == 15: #because nybbles 14 and 15 are actually I/O, we need to check that we're not grabbing those, because they're separate vars
                        A=inputIO
                elif target == 14:
                        A=outputIO
                else:
                        A=RAM[target]
                return ""
        elif upperNybble == 4: #LDA: Load A from immediate (lower nybble stored into A)
                print("DEBUG: LDA "+str(decodeLowerNybble(byteIn)))
                A=decodeLowerNybble(byteIn)
                return ""
        elif upperNybble == 5: #ZJP: Zero Jump. Only if A is 0, jump.
                print("DEBUG: ZJP "+str(decodeLowerNybble(byteIn)))
                if A==0:
                        return decodeLowerNybble(byteIn)
                else:
                        return ""
        elif upperNybble == 6: #LDB: Load B from immediate (lower nybble)
                print("DEBUG: LDB "+str(decodeLowerNybble(byteIn)))
                B=decodeLowerNybble(byteIn)
                return ""
        elif upperNybble == 7: #LBM: Load B from Memory, load A from memory nybble determined by lower nybble
                target = decodeLowerNybble(byteIn)
                print("DEBUG: LBM "+str(target))
                if target == 15:
                        B=inputIO
                elif target == 14:
                        B=outputIO
                else:
                        B=RAM[target]
                return ""
        elif upperNybble == 8: #JMP: Jump, jumps to address determined by lower nybble
                print("DEBUG: JMP "+str(decodeLowerNybble(byteIn)))
                return decodeLowerNybble(byteIn)
        elif upperNybble == 9: #SOM: Store O to Memory, writes O to a memory location determined by lower nybble.
                target = decodeLowerNybble(byteIn)
                print("DEBUG: SOM "+str(target))
                if target == 15:
                        inputIO=O
                elif target == 14:
                        outputIO=O
                        outputNew=1
                else:
                        RAM[target]=O
                return ""
        elif upperNybble == 10: #AND: Bitwise AND A and B, store into O.
                print("DEBUG: AND")
                O=(A&B)%16
                return ""
        elif upperNybble == 11: #OR: Bitwise OR A and B, store into O.
                print("DEBUG: OR")
                O=(A|B)%16
                return ""
        elif upperNybble == 12: #XOR: Bitwise XOR A and B, store into O.
                print("DEBUG: XOR")
                O=(A^B)%16
                return ""
        elif upperNybble == 13: #NND: Bitwise NAND A and B, store into O.
                print("DEBUG: NND")
                O=abs(~(A&B))%16 #this may not work like this out of the box, i may have to split it
                return ""
        elif upperNybble == 14: #NOR: Bitwise NOR A and B, store into O.
                print("DEBUG: NOR")
                O=abs(~(A|B))%16
                return ""
        elif upperNybble == 15: #XNR: Bitwise XNOR A and B, store into O.
                print("DEBUG: XNR")
                O=abs(~(A^B))%16
                return ""
        else:
                print("!!!CRASH!!!: out of bounds opcode found! upperNybble="+str(upperNybble)+",lowerNybble="+str(lowerNybble)) #to catch any funky Python logic, since sometimes it forgets what if statements are
                exit(1)
#handle the emulated keyboard, which doesn't really have to be a keyboard, but we'll just use it as one here because it's easier
def inputHandler(charIn): #charset given working title of "Mini-ASCII"
        global inputIO
        global inputdict
        getresult = inputdict.get(charIn.lower())
        if getresult != None:
                inputIO = getresult
                return ""
        return "INVCHAR"

#handles the emulated screen, which can be anything, really, but here it's a 32-char shift screen
def outputHandler():
        global outputNew
        global outputIO
        global charbuffer
        global outputString
        global outputdict
        if outputNew==1:
                getresult = outputdict.get(outputIO)
                if getresult == None:
                        print("!!!CRASH!!!: out of bounds value sent from CPU! outputIO="+str(outputIO))
                        exit(1)
                charbuffer.append(getresult)
                outputNew = 0
                del charbuffer[0]
        outputString = ""
        for i in charbuffer:
                outputString+=i
        return

#steps the emulator forward one cycle, has some emu logic as well
def doStep():
        global ROM #this sucks ass and i had to repeat it so many times i'm so sorry
        global PC
        global A
        global B
        global O
        global P
        global RAM
        global inputIO
        global outputIO
        global BRK
        global outputNew
        global outputString
        resultCode = ""
        resultCode = doInstruction(ROM[PC]) #we gotta catch jump codes if they pop up, so trap return value
        if resultCode == "": #hacky jump code, but w/e
                PC+=1
        else:
                PC = resultCode
        PC=PC%16 #as PC can't be >15
        print("DEBUG: PC=$"+str(hex(PC)[2:]).upper()+",ROM[PC]=$"+str(ROM[PC]).upper()+",A=$"+str(hex(A)[2:]).upper()+",B=$"+str(hex(B)[2:]).upper()+",O=$"+str(hex(O)[2:]).upper()+",BRK="+str(BRK)+",P="+str("{0:08b}").format(int(P,16))+",OUT=$"+str(hex(outputIO)[2:]).upper()+",IN=$"+str(hex(inputIO)[2:]).upper()+",OUT_NEW="+str(outputNew)) #i'm not sorry for this monster of a line
        print("DEBUG: RAM="+str(RAM))
        print("DEBUG: outputString="+outputString)
        inputIO = 0
        outputHandler()
        return

#the worst command processor ever, like actually this is so very bad, please refactor if possible
def commandprocessor(commandIn):
        global A
        global B
        global O
        global PC
        global P
        global BRK
        global inputIO
        global outputIO
        global outputNew
        global ROM
        global RAM
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
                        outputIO = commandwhat
                elif commandwhere == 15: #handle I/O being split in the emulator
                        inputIO = commandwhat
                else:
                        RAM[commandwhere] = commandwhat
                return ""
        elif commandfunc == "reset" or commandfunc == "reboot" or commandfunc == "restart": #restarts the emulated chip
                initVars()
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
                        initVars()
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
                if BRK == 1:
                        print("Cannot step, BRK processed. Please RESET.") #since a BRK should halt the CPU
                else:
                        commandcount = int(commandcount) #python weirdness catcher
                        if commandcount == None: #if no second argument, just do one
                                doStep()
                        elif int(commandcount) < 1: #how the fuck do we step 0 times? or negative times?
                                return "ARGVAL 1"
                        else:
                                while commandcount != 0 and BRK != 1:
                                        doStep()
                                        commandcount -= 1
                return ""
        elif commandfunc == "run" or commandfunc == "go": #just go infinitely, may add some break support at some point
                if BRK == 1: #since BRK halts the CPU
                        print("Cannot run, BRK processed. Please RESET.")
                else:
                        while BRK != 1:
                                doStep()
                return ""
        elif commandfunc == "output" or commandfunc == "print" or commandfunc == "tell": #print the same info we do on each step
                print("DEBUG: PC=$"+str(hex(PC)[2:]).upper()+",ROM[PC]=$"+str(ROM[PC]).upper()+",A=$"+str(hex(A)[2:]).upper()+",B=$"+str(hex(B)[2:]).upper()+",O=$"+str(hex(O)[2:]).upper()+",BRK="+str(BRK)+",P="+str("{0:08b}").format(int(str(P),16))+",OUT=$"+str(hex(outputIO)[2:]).upper()+",IN=$"+str(hex(inputIO)[2:]).upper()+",OUT_NEW="+str(outputNew)) #i'm not sorry for this monster of a line
                print("DEBUG: RAM="+str(RAM))
                print("DEBUG: outputString="+outputString)
                return ""
        elif commandfunc == "quit" or commandfunc == "exit": #quit emulator
                return "QUIT"
        elif commandfunc == "help" or commandfunc == "what" or commandfunc == "?": # print list of commands, update string when a new one is added
                print("Command processor help:\nWRITE/POKE <where> <what>: Writes to RAM or virtual I/O.\nRESET/REBOOT/RESTART: Reboots the emulated CPU.\nLOAD <filename> (preserve): Loads a ROM. If the \"preserve\" keyword is included, the emulated CPU won't be reset after load.\nINPUT <char>: Writes a character to the emulated CPU's Input I/O. Only valid Mini-ASCII is supported.\nSTEP (count): Steps forward one CPU cycle. If the \"count\" parameter is included, STEP that many cycles at once.\nRUN/GO: Run until BRK processed. Cannot be interrupted, so be careful of infinite loops!\nPRINT/TELL/OUTPUT: Prints debug information (like you get after a STEP.)\nQUIT: Quits the emulator.")
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
commandIn = input("Enter a command to run.\nInput> ") #pre-seed the interpreter
while True: #loop the interpreter
        commandresult = commandprocessor(commandIn) #pass command string to interpreter logic body
        if commandresult != "" and commandresult != "QUIT": #did we error?
                print("ERROR: Command processor returned error: "+commandresult) #tell the user if we did
        if commandresult == "QUIT": #quit the routine
                break #just fall through, exit() spits out an error even if we try code 0
        commandIn = input("Enter a command to run.\nInput> ")
