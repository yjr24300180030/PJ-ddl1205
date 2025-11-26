import sys
import json
from typing import Dict, List, Tuple, Optional
"""
A simple Y86-64 simulator focusing on parsing  '.yo' program files and
producing JSON output after each instruction. The simulator implements
the core Y86 instruction set defined in the project specification.
"""
# --------------------------------
# Constants and type definitions
#---------------------------------

# Maximum memory size
MEM_MAX_SIZE=0x20000

# Status codes 
STAT_AOK=1         #Normal operation
STAT_HLT=2         #Halt encountered
STAT_ADR=3         #Invalid address
STAT_INS=4         #Invalid instruction

# Register names in the order specified in the project description
REG_NAMES=[
    "rax", "rcx", "rdx", "rbx",
    "rsp", "rbp", "rsi", "rdi",
    "r8",  "r9",  "r10", "r11",
    "r12", "r13", "r14"
]

# Register identifiers matching the encoding used in the Y86 machine
# code. Index REG_NONE (0xF) denotes "no register".
REG_ID={
    0x0: 0,     #%rax
    0x1: 1,     #%rcx
    0x2: 2,     #%rdx
    0x3: 3,     #%rbx
    0x4: 4,     #%rsp
    0x5: 5,     #%rbp
    0x6: 6,     #%rsi
    0x7: 7,     #%rdi
    0x8: 8,     #%r8
    0x9: 9,     #%r9
    0xA: 10,    #%r10
    0xB: 11,    #%r11
    0xC: 12,    #%r12
    0xD: 13,    #%r13
    0xE: 14,    #%r14
    0xF: None   # No register
}

def twos_complement_to_signed(val: int)->int:
    """
    将一个64位无符号整数转换为Python中的有符号整数,
    Y86使用的是64位二进制补码运算,要在Python中表示负数,
    对于最高位为1的值,要用该值减去2**64。
    """
    if val&(1<<63):
        return val-(1<<64)
    return val

def parse_yo_stream(stream: List[str])->Dict[int, int]:
    memory: Dict[int, int]={}
    for line in stream:
        s=line.rstrip()
        if not s:
            continue
        if ':' not in s:
            continue
        left, *_=s.split('|', 1)
        left=left.strip()
        if not left:
            continue
        try:
            addr_str, hex_str=left.split(':', 1)
        except ValueError:
            continue
        addr_str=addr_str.strip()
        hex_str=hex_str.strip().replace(' ', '')
        if not hex_str
            continue
        try:
            base_addr=int(addr_str, 16)
        except ValueError:
            continue
        if base_addr>=MEM_MAX_SIZE:
            continue
        if len(hex_str)%2==1:
            hex_str=hex_str+'0'
        for i in range(0, len(hex_str), 2):
            byte_val=int(hex_str[i:i+2], 16)
            addr=base_addr+(i//2)
            if addr<MEM_MAX_SIZE:
                memory[addr]=byte_val
    return memory

