import os
import sys
from miasm2.jitter.csts import PAGE_READ, PAGE_WRITE
from miasm2.analysis.machine import Machine
from pdb import pm

# Shellcode
# main:
#       MOV    EAX, 0x10
#       MOV    EBX, 0x1
# loop_main:
#       SUB    EAX, 0x1
#       CMOVZ  ECX, EBX
#       JNZ    loop_main
# loop_end:
#       RET


data = "b810000000bb0100000083e8010f44cb75f8c3".decode("hex")
run_addr = 0x40000000

def code_sentinelle(jitter):
    jitter.run = False
    jitter.pc = 0
    return True

def init_jitter():
    global data, run_addr
    # Create jitter
    myjit = Machine("x86_32").jitter(sys.argv[1])

    myjit.vm.add_memory_page(run_addr, PAGE_READ | PAGE_WRITE, data)

    # Init jitter
    myjit.init_stack()
    myjit.jit.log_regs = True
    myjit.jit.log_mn = True
    myjit.push_uint32_t(0x1337beef)

    myjit.add_breakpoint(0x1337beef, code_sentinelle)
    return myjit

# Test 'max_exec_per_call'
print "[+] First run, to jit blocks"
myjit = init_jitter()
myjit.init_run(run_addr)
myjit.continue_run()

assert myjit.run is False
assert myjit.cpu.EAX  == 0x0

## Let's specify a max_exec_per_call
## 5: main/loop_main, loop_main
myjit.jit.options["max_exec_per_call"] = 5

first_call = True
def cb(jitter):
    global first_call
    if first_call:
        # Avoid breaking on the first pass (before any execution)
        first_call = False
        return True
    return False

## Second run
print "[+] Second run"
myjit.push_uint32_t(0x1337beef)
myjit.cpu.EAX = 0
myjit.init_run(run_addr)
myjit.exec_cb = cb
myjit.continue_run()

assert myjit.run is True
# Use a '>=' because it's a 'max_...'
assert myjit.cpu.EAX >= 0xA

# Test 'jit_maxline'
print "[+] Run instr one by one"
myjit = init_jitter()
myjit.jit.options["jit_maxline"] = 1
myjit.jit.options["max_exec_per_call"] = 1

counter = 0
def cb(jitter):
    global counter
    counter += 1
    return True

myjit.init_run(run_addr)
myjit.exec_cb = cb
myjit.continue_run()

assert myjit.run is False
assert myjit.cpu.EAX  == 0x00
## main(2) + (loop_main(3))*(0x10) + loop_end(1) + 0x1337beef (1)
assert counter == 52
