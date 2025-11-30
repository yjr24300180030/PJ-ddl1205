#include "cpu.h"
#include <iostream>
#include <fstream>
#include <iomanip> 

Simulator::Simulator() {
    PC = 0;
    stat = STAT_AOK;
    icode = I_NOP;
    ifun = 0;
    // 清空寄存器
    for (int i = 0; i < 15; ++i) reg[i] = 0;
    cc.zf = true; 
    cc.sf = false; 
    cc.of = false;
}

bool Simulator::check_condition(int ifun, bool zf, bool sf, bool of) {
    bool lt = (sf ^ of);        // Less Than
    bool eq = zf;               // Equal
    bool le = (lt || eq);       // Less or Equal
    bool ne = !zf;              // Not Equal
    bool ge = !lt;              // Greater or Equal
    bool gt = !le;              // Greater Than

    switch (ifun) {
        case F_JMP: return true; // 0: Uncond
        case F_JLE: return le;   // 1: <=
        case F_JL:  return lt;   // 2: <
        case F_JE:  return eq;   // 3: ==
        case F_JNE: return ne;   // 4: !=
        case F_JGE: return ge;   // 5: >=
        case F_JG:  return gt;   // 6: >
        default:    return false;
    }
}

void Simulator::fetch() {
    bool imem_error = false; 

    // 1. 读取第一个字节
    if (memory.find(PC) == memory.end() && PC < MEM_MAX_SIZE) {
        // 如果map里没找到，但地址在范围内，视为0 (NOP/Halt)，或者报错
        // 通常未初始化的内存读作0
        // 但如果 PC 超过 MEM_MAX_SIZE，则是错误
    }
    
    if (PC >= MEM_MAX_SIZE) {
        imem_error = true;
    }

    if (imem_error) {
        stat = STAT_ADR;
        return;
    }

    // 从 map 中读取，若不存在默认是 0
    byte_t byte0 = 0;
    if (memory.find(PC) != memory.end()) {
        byte0 = memory[PC];
    }
    
    icode = (byte0 >> 4) & 0xF;
    ifun  = byte0 & 0xF;

    // 2. 检查指令合法性
    if (icode > I_POPQ) {
        stat = STAT_INS;
        return;
    }
    
    // 3. 判断指令结构
    bool need_reg = (icode == I_RRMOVQ || icode == I_OPQ || icode == I_PUSHQ || 
                     icode == I_POPQ || icode == I_IRMOVQ || icode == I_RMMOVQ || 
                     icode == I_MRMOVQ);

    bool need_valC = (icode == I_IRMOVQ || icode == I_RMMOVQ || icode == I_MRMOVQ || 
                      icode == I_JXX || icode == I_CALL);

    // 4. 读取后续字节
    addr_t tempPC = PC + 1;

    if (need_reg) {
        if (tempPC >= MEM_MAX_SIZE) {
            stat = STAT_ADR;
            return;
        }
        
        byte_t byte_reg = 0;
        if (memory.find(tempPC) != memory.end()) {
            byte_reg = memory[tempPC];
        }

        rA = (byte_reg >> 4) & 0xF;
        rB = byte_reg & 0xF;
        tempPC += 1;
    } else {
        rA = REG_NONE; 
        rB = REG_NONE; 
    }

    if (need_valC) {
        valC = readMemoryWord(tempPC, imem_error);
        if (imem_error) {
            stat = STAT_ADR;
            return;
        }
        tempPC += 8;
    } else {
        valC = 0;
    }

    // 5. 计算 valP
    valP = tempPC;

    // 6. Halt 检查
    if (icode == I_HALT) {
        stat = STAT_HLT;
    }
}

void Simulator::decode() {
    // 1. 读取 valA
    byte_t srcA = REG_NONE;
    if (icode == I_RRMOVQ || icode == I_RMMOVQ || icode == I_OPQ || icode == I_PUSHQ) {
        srcA = rA;
    } else if (icode == I_POPQ || icode == I_RET) {
        srcA = REG_RSP;
    }

    if (srcA != REG_NONE) {
        // 安全检查
        if (srcA >= 0 && srcA <= 14) valA = reg[srcA];
        else valA = 0; 
    } else {
        valA = 0;
    }

    // 2. 读取 valB
    byte_t srcB = REG_NONE;
    if (icode == I_OPQ || icode == I_RMMOVQ || icode == I_MRMOVQ) {
        srcB = rB;
    } else if (icode == I_PUSHQ || icode == I_POPQ || icode == I_CALL || icode == I_RET) {
        srcB = REG_RSP;
    }

    if (srcB != REG_NONE) {
        if (srcB >= 0 && srcB <= 14) valB = reg[srcB];
        else valB = 0;
    } else {
        valB = 0;
    }
}

void Simulator::execute() {
    Cnd = false; 
    valE = 0;

    long long aluA = (long long)valA;
    long long aluB = (long long)valB; 
    
    switch (icode) {
        case I_OPQ: {
            if (ifun == F_ADD) valE = aluB + aluA;
            else if (ifun == F_SUB) valE = aluB - aluA;
            else if (ifun == F_AND) valE = aluB & aluA;
            else if (ifun == F_XOR) valE = aluB ^ aluA;
            
            // 强制转换 valE 检查符号位
            cc.zf = (valE == 0);
            cc.sf = ((long long)valE < 0);
            
            if (ifun == F_ADD) {
                bool pos_over = (aluA > 0 && aluB > 0 && (long long)valE < 0);
                bool neg_over = (aluA < 0 && aluB < 0 && (long long)valE >= 0);
                cc.of = pos_over || neg_over;
            } else if (ifun == F_SUB) {
                bool pos_over = (aluB < 0 && aluA > 0 && (long long)valE >= 0); 
                bool neg_over = (aluB > 0 && aluA < 0 && (long long)valE < 0); 
                cc.of = pos_over || neg_over;
            } else {
                cc.of = false; 
            }
            break; 
        }

        case I_RRMOVQ: 
            valE = valA;
            Cnd = check_condition(ifun, cc.zf, cc.sf, cc.of);
            break;
            
        case I_IRMOVQ: 
            valE = valC; 
            break;
            
        case I_RMMOVQ:
        case I_MRMOVQ:
            valE = valB + valC; 
            break;
            
        case I_CALL:
        case I_PUSHQ:
            valE = valB - 8; 
            break;
            
        case I_POPQ:
        case I_RET:
            valE = valB + 8;
            break;

        case I_JXX: 
            Cnd = check_condition(ifun, cc.zf, cc.sf, cc.of); 
            break;
            
        default: break;
    }
}

void Simulator::memory_access() {
    addr_t mem_addr = 0;
    if (icode == I_RMMOVQ || icode == I_PUSHQ || icode == I_CALL || icode == I_MRMOVQ) {
        mem_addr = valE;
    } else if (icode == I_POPQ || icode == I_RET) {
        mem_addr = valA;
    }

    bool mem_read = (icode == I_MRMOVQ || icode == I_POPQ || icode == I_RET);
    bool mem_write = (icode == I_RMMOVQ || icode == I_PUSHQ || icode == I_CALL);
    bool error = false;

    if (mem_read) {
        valM = readMemoryWord(mem_addr, error);
    } 
    
    if (mem_write) {
        word_t data = (icode == I_CALL) ? valP : valA;
        writeMemoryWord(mem_addr, data, error);
    }

    if (error) {
        stat = STAT_ADR;
    }
}

void Simulator::write_back() {
    byte_t dstE = REG_NONE;
    if (icode == I_RRMOVQ) {
        if (Cnd) dstE = rB;
    } 
    else if (icode == I_IRMOVQ || icode == I_OPQ) {
        dstE = rB;
    }
    else if (icode == I_PUSHQ || icode == I_POPQ || icode == I_CALL || icode == I_RET) {
        dstE = REG_RSP; 
    }

    byte_t dstM = REG_NONE;
    if (icode == I_MRMOVQ || icode == I_POPQ) {
        dstM = rA; 
    }

    if (dstE != REG_NONE) reg[dstE] = valE;
    if (dstM != REG_NONE) reg[dstM] = valM;
}

void Simulator::pc_update() {
    // 修复：如果状态不是 AOK (比如遇到了 HALT 或 错误)，不要移动 PC
    if (stat != STAT_AOK) {
        return;
    }

    PC = valP;
    switch (icode) {
        case I_CALL: PC = valC; break;
        case I_JXX:  if (Cnd) PC = valC; break;
        case I_RET:  PC = valM; break;
        default: break;
    }
}


word_t Simulator::readMemoryWord(addr_t addr, bool& error) {
    if (addr >= MEM_MAX_SIZE || addr + 8 > MEM_MAX_SIZE) { 
    // 注意：如果是负数地址(巨大正数)，addr >= MEM_MAX_SIZE 直接就能拦住
    error = true;
    return 0;
    }
    error = false;
    word_t val = 0;
    for (int i = 0; i < 8; ++i) {
        // 读取字节，若map中没有则为0
        word_t byte_val = 0;
        if (memory.find(addr + i) != memory.end()) {
            byte_val = memory[addr + i];
        }
        val |= ((word_t)(byte_t)byte_val) << (i * 8);
    }
    return val;
}

void Simulator::writeMemoryWord(addr_t addr, word_t val, bool& error) {
    if (addr >= MEM_MAX_SIZE || addr + 8 > MEM_MAX_SIZE) {
    error = true;
    return;
    }
    error = false;
    uint64_t uval = (uint64_t)val;
    for (int i = 0; i < 8; ++i) {
        memory[addr + i] = (uval >> (i * 8)) & 0xFF;
    }
}

void Simulator::loadProgram(const std::string& filename) {
    std::ifstream fin(filename);
    if (!fin.is_open()) {
        std::cerr << "Cannot open file: " << filename << std::endl;
        return;
    }
    addr_t addr;
    int val;
    // 配合parser: 十进制地址 + 十六进制数值
    while (fin >> std::dec >> addr >> std::hex >> val) {
        if (addr < MEM_MAX_SIZE) {
            memory[addr] = (byte_t)val;
        }
    }
    fin.close();
}

void Simulator::dumpJson() {
    std::cout << "{"; 

    // 1. CC
    std::cout << "\"CC\":{";
    std::cout << "\"OF\":" << (cc.of ? 1 : 0) << ",";
    std::cout << "\"SF\":" << (cc.sf ? 1 : 0) << ",";
    std::cout << "\"ZF\":" << (cc.zf ? 1 : 0);
    std::cout << "},"; 

    // 2. MEM 
    // 【关键修改】这里是把散乱的字节拼成 Word
    std::cout << "\"MEM\":{";
    std::map<addr_t, uint64_t> word_mem;
    for (auto const& [addr, byte_val] : memory) {
        addr_t word_addr = addr & ~0x7; 
        int shift = (addr % 8) * 8;
        word_mem[word_addr] |= ((uint64_t)byte_val << shift);
    }

    bool first = true;
    for (auto const& [addr, val] : word_mem) {
        if (!first) std::cout << ",";
        // 【核心修复】必须强转为 (int64_t) 才能打印出负数！
        // 之前是 val (uint64_t)，所以打印出了 huge positive number
        std::cout << "\"" << std::dec << addr << "\":" << (int64_t)val;
        first = false;
    }
    std::cout << "},"; 

    // 3. PC
    std::cout << "\"PC\":" << std::dec << PC << ",";

    // 4. REG
    std::cout << "\"REG\":{";
    const char* names[] = {"rax","rcx","rdx","rbx","rsp","rbp","rsi","rdi","r8","r9","r10","r11","r12","r13","r14"};
    for (int i = 0; i < 15; ++i) {
        if (i > 0) std::cout << ",";
        std::cout << "\"" << names[i] << "\":" << std::dec << (long long)reg[i];
    }
    std::cout << "},"; 

    // 5. STAT
    std::cout << "\"STAT\":" << std::dec << stat;

    std::cout << "}"; 
}


void Simulator::run() {
    int max_steps = 10000;
    int steps = 0;
    std::cout << "["; 
    while (stat == STAT_AOK && steps < max_steps) {
        if (steps > 0) std::cout << ",";
        fetch();
        decode();
        execute();
        memory_access();
        write_back();
        pc_update();
        dumpJson();
        steps++;
    }
    std::cout << "]" << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 2) return 1; 
    Simulator sim;
    sim.loadProgram(argv[1]);
    sim.run();
    return 0;
}
