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
    """
    从行序列中解析.yo程序,参数stream:List[str]从.yo文件读取的行列表,
    返回值:Dict[int, int]从内存地址到字节值的映射。显式出现在.yo文件中
    的地址被填充,其他地址默认存储0
    """
    memory: Dict[int, int]={}
    for line in stream:
        # 去除末尾的换行符和首尾空白字符
        s=line.rstrip()
        if not s:
            continue
        # 跳过不包含冒号的行
        if ':' not in s:
            continue
        # 提取地址和竖线前的代码部分
        left, *_=s.split('|', 1)
        left=left.strip()
        if not left:
            continue
        # 分离地址和十六进制字符串
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
        # 跳过格式错误的地址
            continue
        if base_addr>=MEM_MAX_SIZE:
            continue
        # 将十六进制字符串转换为字节,如果hex_str长度为奇数,在右侧填充
        if len(hex_str)%2==1:
            hex_str=hex_str+'0'
        for i in range(0, len(hex_str), 2):
            byte_val=int(hex_str[i:i+2], 16)
            addr=base_addr+(i//2)
            if addr<MEM_MAX_SIZE:
                memory[addr]=byte_val
    return memory

class Simulator:
    """
    Y86-64模拟器核心类,该模拟器维护处理器状态(程序计数器、寄存器、内存、条件码和状态字),
    并执行指令直至满足终止条件。每条指令执行后,当前状态会被追加到日志中用于生成JSON输出。
    """
    def __init__(self, memory: Dict[int, int]):
        #初始程序计数器
        self.pc: int=0
        #通用寄存器,15个条目对应rax到r14
        self.reg: List[int]=[0]*15
        self.zf: int=1      #零标志初始化为1
        self.sf: int=0      #符号标志
        self.of: int=0      #溢出标志
        #处理器状态
        self.stat: int=STAT_AOK
        #字节地址到字节值的映射
        self.mem: Dict[int, int]=memory.copy()
        #用于JSON输出的8字节对齐内存组,将基地址映射到有符号64位值
        self.mem_groups: Dict[int, int]={}
        #构建初始内存组
        self._init_mem_groups()
#--------------------------------
# 内存操作辅助方法
#--------------------------------
    def _init_mem_groups(self)->None:
        #基于当前内存内容初始化mem_groups
        for addr in self.mem:
            base=(addr//8)*8
            if base not in self.mem_groups:
                self.update_mem_group(base)
    
    def _update_mem_group(self, base: int)->None:
        if base>=MEM_MAX_SIZE:
            return  
        val=0
        for i in range(8):
            b=self.mem.get(base+i, 0)
            val|=(b&0xFF)<<(8*i)
        if val==0:
            self.mem_groups.pop(base, None)
        else:
            self.mem_groups[base]=twos_complement_to_signed(val)  
    
    def _read_word(self, addr: int)->Tuple[int, bool]:
        if addr<0 or addr+8>MEM_MAX_SIZE:
            return 0, True
        val=0
        for i in range(8):
            val|=(self.mem.get(addr+i,0)&0xFF)<<(8*i)
        return twos_complement_to_signed(val), False

    def _write_word(self, addr:int, value:int)->bool:
        if addr<0 or addr+8>MEM_MAX_SIZE:
            return False
        uval=value&(0xFFFFFFFFFFFFFFFF)
        for i in range(8):
            byte=(uval>>(8*i))&0xFF
            self.mem[addr+i]=byte
            affected_bases.add(((addr+i)//8)*8)
        for base in affected_bases:
            self._update_mem_group(base)
        return True
#--------------------------------
# 执行
#--------------------------------
    def _set_cc(self, result:int, op:str, a:int, b:int)->None:
    # 根据ALU运算设置条件码
    """
    result: ALU运算结果,int
    op: 操作类型,str, 'add','sub','and','xor'
    a,b: 操作数,int,用于溢出检测
    """
        self.zf=1 if result==0 else 0
        #将结果转换为无符号64位以检查符号位
        self.sf=1 if (result&(1<<63))!=0 else 0
        #溢出标志
        of=0 
        if op=='add':
            #当操作数符号相同且结果符号不同,发生溢出
            if((a>=0 and b>=0 and result<0) or (a<0 and b<0 and result>=0)):
                of=1
        elif op=='sub':
            #a-b溢出检测等价于a+(-b)的溢出检测,当a和-b符号相同且结果符号不同,发生溢出
            neg_b=-b
            if((a>=0 and neg_b>=0 and result<0) or (a<0 and neg_b<0 and result>=0)):
                of=1
        else:
            #与和异或操作不产生溢出
            of=0
        self.of=of
    
    def _cond(self, fun:int)->bool:
        """
        根据处理器的条件码状态评估条件分支的条件是否满足
        如果应该执行分支,返回True,否则返回False
        """
        ZF=self.zf
        SF=self.sf
        OF=self.of
        if fun==0:              #无条件
            return True
        elif fun==1:            #le,小于等于
            return (SF^OF) or ZF
        elif fun==2:            #l,小于
            return (SF^OF)==1
        elif fun==3:            #e,等于
            return ZF==1
        elif fun==4:            #ne,不等于
            return ZF==0
        elif fun==5:            #ge,大于等于
            return (SF^OF)==0
        elif fun==6:            #g,大于
            return (SF^OF)==0 and (ZF==0)
        else:                   #无效的条件码
            return False
#--------------------------------
# 主执行循环
#--------------------------------
    def run(self, max_steps: int=100000)->List[Dict[str, object]]:
        log: List[Dict[str, object]]=[]
        steps=0
        while self.stat==STAT_AOK and steps<max_steps:
            steps+=1
            if self.pc>=MEM_MAX_SIZE:
                self.stat=STAT_ADR
                break
            byte0=self.mem.get(self.pc, 0)
            icode=(byte0>>4)&0xF
            ifun=byte0&0xF
            pc_curr=self.pc
            pc_next=self.pc+1
            rA: Optional[int]=None
            rB: Optional[int]=None
            valC: Optional[int]=None
            
            try:
                if icode==0x0:
                    pc_next=self.pc
                    self.stat=STAT_HLT
                elif icode==0x1:
                    pc_next=self.pc+1
                elif icode==0x2:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    reg_byte=self.mem.get(pc_next, 0)
                    rA_id=(reg_byte>>4)&0xF
                    rB_id=reg_byte&0xF
                    rA=REG_ID.get(rA_id)
                    rB=REG_ID.get(rB_id)
                    if rA is None or rB is None:
                        self.stat=STAT_INS
                        break
                    pc_next+=1
                    valA=self.reg[rA]
                    if 0<=ifun<=6:
                        cond=self._cond(ifun)
                        if cond:
                            self.reg[rB]=valA
                    else:
                        self.stat=STAT_INS
                        break
                elif icode==0x3:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    reg_byte=self.mem.get(pc_next, 0)
                    rA_id=(reg_byte>>4)&0xF
                    rB_id=reg_byte&0xF
                    rA=REG_ID.get(rA_id)
                    rB=REG_ID.get(rB_id)
                    if rB is None:
                        self.stat=STAT_INS
                        break
                    pc_next+=1
                    if pc_next+8>MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    uval=0
                    for i in range(8):
                        uval|=(self.mem.get(pc_next+i, 0)&0xFF)<<(8*i))
                    valC=twos_complement_to_signed(uval)
                    pc_next+=8
                    self.reg
                elif icode==0x4:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    reg_byte=self.mem.get(pc_next, 0)
                    rA_id=(reg_byte>>4)&0xF
                    rB_id=reg_byte&0xF
                    rA=REG_ID.get(rA_id)
                    rB=REG_ID.get(rB_id)
                    if rA is None or rB is None:
                        self.stat=STAT_INS
                        break
                    pc_next+=1
                    valA=self.reg[rA]
                    valB=self.reg[rB]
                    result: int=0
                    if ifun==0x0:
                        result=valB+valA
                        self._set_cc(result, 'add', valB, valA)
                    elif ifun==0x1:
                        result=valB-valA
                        self._set_cc(result, 'sub', valB, valA)
                    elif ifun==0x2:
                        result=valB&valA
                        self._set_cc(result, 'and', valB, valA)
                    elif ifun==0x3:
                        result=valB^valA
                        self._set_cc(result, 'xor', valB, valA)
                    else:
                        self.stat=STAT_INS
                        break
                    self.reg[rB]=result&0xFFFFFFFFFFFFFFFF
                elif icode==0x7:
                    if pc_next+8>MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    uval=0
                    for i in range(8):
                        uval|=(self.mem.get(pc_next+i, 0)&0xFF)<<(8*i)
                    valC=twos_complement_to_signed(uval)
                    pc_next+=8
                    coud=self._cond(ifun)
                    if 0<=ifun<=6:
                        if coud:
                            pc_next=valC
                    else:
                        self.stat=STAT_INS
                        break
                elif icode==0x8:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    uval=0
                    for i in range(8):
                        uval|=(self.mem.get(pc_next+i, 0)&0xFF)<<(8*i)
                    valC=twos_complement_to_signed(uval)
                    pc_next+=8
                    rsp_val=self.reg[4]
                    new_rsp=rsp_val-8
                    self.reg[4]=new_rsp
                    ok=self._write_word(new_rsp, pc_next)
                    if not ok:
                        self.stat=STAT_ADR
                        pc_next=pc_curr
                        break
                    pc_next=valC
                elif icode==0x9:
                    rsp_val=self.reg[4]
                    ret_addr, err=self._read_word(rsp_val)
                    if err:
                        self.stat=STAT_ADR
                        break
                    new_rsp=rsp_val+8
                    self.reg[4]=new_rsp
                    pc_next=ret_addr
                elif icode==0xA:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    reg_byte=self.mem.get(pc_next, 0)
                    rA_id=(reg_byte>>4)&0xF
                    rA=REG_ID.get(rA_id)
                    if rA is None:
                        self.stat=STAT_INS
                        break
                    pc_next+=1
                    valA=twos_complement_to_signed(self.reg[rA]&0xFFFFFFFFFFFFFFFF)
                    rsp_val=self.reg[4]
                    new_rsp=rsp_val-8
                    self.reg[4]=new_rsp
                    ok=self._write_word(new_rsp, valA)
                    if not ok:
                        self.stat=STAT_ADR
                        pc_next=pc_curr
                        break
                elif icode==0xB:
                    if pc_next>=MEM_MAX_SIZE:
                        self.stat=STAT_ADR
                        break
                    reg_byte=self.mem.get(pc_next, 0)
                    rA_id=(reg_byte>>4)&0xF
                    rA=REG_ID.get(rA_id)
                    if rA is None:
                        self.stat=STAT_INS
                        break
                    pc_next+=1
                    rsp_val=self.reg[4]
                    val, err=self._read_word(rsp_val)
                    if err:
                        self.stat=STAT_ADR
                        break
                    new_rsp=rsp_val+8
                    self.reg[4]=new_rsp
                    self.reg[rA]=val
                else:
                    self.stat=STAT_INS
                    break
            except Exception:
                self.stat=STAT_INS
                break
            self.pc=pc.next&0xFFFFFFFFFFFFFFFF
            log.append(self._snapshot_state())
        if self.stat!=STAT_AOK:
            if not log or log[-1]["STAT"]==STAT_AOK:
                log.append(self._snapshot_state())
        return log
            