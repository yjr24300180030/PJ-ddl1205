#include "cpu.h"
#include <fstream>
Simulator::Simulator() {
    PC = 0;
    stat = STAT_AOK;
    icode = I_NOP;
    ifun = 0;
    // 清空寄存器和条件码
    for (int i = 0; i < 15; ++i) reg[i] = 0;
    cc.ZF = true; cc.SF = false; cc.OF = false;
}

bool Simulator::check_condition(int ifun, bool zf, bool sf, bool of) {

    bool lt = sf ^ of; 

    bool le = lt || zf;

    bool gt = !le;      

    bool ne = !zf;      

    switch (ifun) {
        case F_JMP: return true; // 0x0: 无条件 (jmp, rrmovq)
        case F_JLE: return le;   // 0x1: <=
        case F_JL:  return lt;   // 0x2: <
        case F_JE:  return zf;   // 0x3: ==
        case F_JNE: return ne;   // 0x4: !=
        case F_JGE: return !lt;   // 0x5: >=
        case F_JG:  return gt;   // 0x6: >
        default:    return false;
    }

}
void Simulator::fetch() {
    // 初始化 fetch 阶段产生的信号
    bool imem_error = false; 

    // ---------------------------------------------------------
    // 1. 读取第一个字节 (icode:ifun)
    // ---------------------------------------------------------
    if (memory.find(PC) == memory.end() || PC >= MEM_MAX_SIZE) {
        imem_error = true;
    }
    
    // 如果地址非法，直接停止，不要往下走了
    if (imem_error) {
        stat = STAT_ADR;
        return;
    }

    byte_t byte0 = memory[PC]; // 读取指令字节
    icode = (byte0 >> 4) & 0xF;
    ifun  = byte0 & 0xF;

    // ---------------------------------------------------------
    // 2. 检查指令是否合法 (Instruction Validity)
    // ---------------------------------------------------------
    // 如果 icode 超出范围，或者具体的指令 icode 合法但 ifun 不合法
    // 可以在这里加更细致的检查，简单版只查 icode
    if (icode > I_POPQ) {
        stat = STAT_INS;
        return;
    }
    
    // ---------------------------------------------------------
    // 3. 判断指令结构 (根据 Y86 规范)
    // ---------------------------------------------------------
    bool need_reg = (icode == I_RRMOVQ || icode == I_OPQ || icode == I_PUSHQ || 
                     icode == I_POPQ || icode == I_IRMOVQ || icode == I_RMMOVQ || 
                     icode == I_MRMOVQ);

    bool need_valC = (icode == I_IRMOVQ || icode == I_RMMOVQ || icode == I_MRMOVQ || 
                      icode == I_JXX || icode == I_CALL);

    // ---------------------------------------------------------
    // 4. 逐步读取后续字节
    // ---------------------------------------------------------
    addr_t tempPC = PC + 1; // 指针移动到下一个字节

    // --- 读取寄存器字节 rA:rB ---
    if (need_reg) {
        // 再次检查内存边界
        if (tempPC >= MEM_MAX_SIZE) {
            stat = STAT_ADR;
            return;
        }
        
        byte_t byte_reg = memory[tempPC];
        rA = (byte_reg >> 4) & 0xF;
        rB = byte_reg & 0xF;
        tempPC += 1;
    } else {
        rA = REG_NONE; // 0xF
        rB = REG_NONE; // 0xF
    }

    // --- 读取立即数 valC (8字节) ---
    if (need_valC) {
        // 调用 helper 函数读取 8 字节
        // 注意：readMemoryWord 会检查 tempPC 到 tempPC+7 是否合法
        valC = readMemoryWord(tempPC, imem_error);
        
        if (imem_error) {
            stat = STAT_ADR;
            return;
        }
        tempPC += 8;
    } else {
        valC = 0;
    }

    // ---------------------------------------------------------
    // 5. 计算 valP (下一条指令地址)
    // ---------------------------------------------------------
    valP = tempPC;

    // ---------------------------------------------------------
    // 6. (可选) 检查 Halt 指令
    // ---------------------------------------------------------
    if (icode == I_HALT) {
        stat = STAT_HLT;
        // 注意：遇到 halt 时，valP 依然指向 halt 的下一个字节
        // 但下一周期并不会执行它，因为 stat 变了，run 循环会退出
    }
}

void Simulator::pc_update() {
    // 默认情况：PC 走向下一条指令
    PC = valP;

    switch (icode) {
        case I_CALL:
            PC = valC; // Call 跳转到立即数地址
            break;
        case I_JXX:
            if (Cnd) PC = valC; // 条件满足才跳
            break;
        case I_RET:
            PC = valM; // Ret 跳到栈里读出的地址
            break;
        default:
            break;
    }
}


void Simulator::loadProgram(const std::string& filename) {
    // 注意：这里 filename 应该是 Python 生成的那个 .input 文件
    std::ifstream fin(filename);
    
    if (!fin.is_open()) {
        std::cerr << "Cannot open file: " << filename << std::endl;
        return;
    }

    addr_t addr;
    int val; // 用 int 读，然后强转 byte_t
    
    // 疯狂读取：地址 数值
    // 因为文件里已经是十进制了，C++ 默认就按十进制读
    while (fin >> addr >> std::hex >> val)  {
        memory[addr] = (byte_t)val;
    }
    
    fin.close();
}
void Simulator::decode() {
    // ==========================================================
    // 1. 读取 valA (源: srcA)
    // ==========================================================
    // ... (之前的逻辑确定 srcA) ...

    if (srcA != REG_NONE) {
        if (srcA >= 0 && srcA <= 14) { // 假设 reg 数组大小为 15
            valA = reg[srcA];
        } else {
            valA = 0;
            stat = STAT_INS; 
        }
    } else {
        valA = 0;
    }

    // ==========================================================
    // 2. 读取 valB (源: srcB)
    // ==========================================================
    // ... (之前的逻辑确定 srcB) ...

    if (srcB != REG_NONE) {
        // --- 增加：安全检查 ---
        if (srcB >= 0 && srcB <= 14) {
            valB = reg[srcB];
        } else {
            valB = 0;
            // stat = STAT_INS;
        }
    } else {
        valB = 0;
    }
}


word_t Simulator::readMemoryWord(addr_t addr, bool& error) {
    // 1. 边界检查
    if (addr + 8 > MEM_MAX_SIZE) {
        error = true;
        return 0;
    }
    
    error = false;
    word_t val = 0;
    
    // 2. 小端序读取 (Little Endian)
    // 低地址存低字节，高地址存高字节
    // val = b0 | (b1 << 8) | (b2 << 16) ...
    for (int i = 0; i < 8; ++i) {
        word_t byte_val = memory[addr + i]; // 读取1字节
        // 这里的 byte_val 必须转为 unsigned long long 再移位，否则可能符号扩展
        val |= ((word_t)(byte_t)byte_val) << (i * 8);
    }
    
    return val;
}

void Simulator::writeMemoryWord(addr_t addr, word_t val, bool& imem_error) {
    // 1. 边界检查
    // 如果起始地址越界，或者跨越了内存边界
    if (addr + 8 > MEM_MAX_SIZE) {
        imem_error = true;
        return;
    }

    imem_error = false;

    // 2. 小端序写入 (Little Endian Splitting)
    // val 的低8位 -> 存入 addr
    // val 的高8位 -> 存入 addr + 7
    // 使用无符号转换防止符号位干扰右移
    uint64_t uval = (uint64_t)val;

    for (int i = 0; i < 8; ++i) {
        byte_t byte_val = (uval >> (i * 8)) & 0xFF;
        memory[addr + i] = byte_val;
    }
}

void Simulator::memory_access() {
    // 1. 确定内存操作的地址 (Mem Addr)
    // 大部分指令用 valE (算出来的地址)
    // POPQ 和 RET 用 valA (栈指针 %rsp 的值)
    addr_t mem_addr = 0;
    if (icode == I_RMMOVQ || icode == I_PUSHQ || icode == I_CALL || icode == I_MRMOVQ) {
        mem_addr = valE;
    } else if (icode == I_POPQ || icode == I_RET) {
        mem_addr = valA;
    }

    // 2. 确定是否读写 (Read/Write Control)
    bool mem_read = (icode == I_MRMOVQ || icode == I_POPQ || icode == I_RET);
    bool mem_write = (icode == I_RMMOVQ || icode == I_PUSHQ || icode == I_CALL);

    // 3. 执行操作
    bool error = false;

    if (mem_read) {
        // 读出的值存入流水线寄存器 valM
        valM = readMemoryWord(mem_addr, error);
    } 
    
    if (mem_write) {
        // 写入的值通常是 valA (寄存器里的值)
        // 只有 CALL 指令是把 valP (返回地址) 压栈
        word_t data = (icode == I_CALL) ? valP : valA;
        writeMemoryWord(mem_addr, data, error);
    }

    // 4. 错误处理
    if (error) {
        stat = STAT_ADR;
    }
}
void Simulator::execute() {
    // 初始化
    Cnd = false; 
    valE = 0;

    // 类型转换
    long long aluA = (long long)valA;
    long long aluB = (long long)valB; 
    
    switch (icode) {
        // A. 运算指令
        case I_OPQ: {
            if (ifun == F_ADD) valE = aluB + aluA;
            else if (ifun == F_SUB) valE = aluB - aluA;
            else if (ifun == F_AND) valE = aluB & aluA;
            else if (ifun == F_XOR) valE = aluB ^ aluA;
            
            // 设置条件码 
            cc.ZF = (valE == 0);
            cc.SF = ((int64_t)valE < 0);
            
            if (ifun == F_ADD) {
                bool pos_over = (aluA > 0 && aluB > 0 && valE < 0);
                bool neg_over = (aluA < 0 && aluB < 0 && valE >= 0);
                cc.OF = pos_over || neg_over;
            } else if (ifun == F_SUB) {
                bool pos_over = (aluB < 0 && aluA > 0 && valE >= 0); 
                bool neg_over = (aluB > 0 && aluA < 0 && valE < 0); 
                cc.OF = pos_over || neg_over;
            } else {
                cc.OF = false; 
            }
            break; 
        }

        // B. 传送指令 (关键修正点！)
        case I_RRMOVQ: // 包含 rrmovq 和 cmovxx
            valE = valA;
            Cnd = check_condition(ifun, cc.ZF, cc.SF, cc.OF);
            break;
            
        case I_IRMOVQ: 
            valE = valC; 
            break;
            
        // C. 内存/栈/跳转指令 (保持不变)
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
            Cnd = check_condition(ifun, cc.ZF, cc.SF, cc.OF); 
            break;
            
        case I_NOP:
        case I_HALT:
            break;
    }
}
void Simulator::write_back() {
    // ==========================================================
    // 1. 确定 dstE 
    //    valE 来自 ALU 计算 (add, sub...) 或 栈指针计算 (rsp +/- 8)
    // ==========================================================
    byte_t dstE = REG_NONE;

    // 情况 A: 条件传送 (cmovXX) / 普通传送 (rrmovq)
    if (icode == I_RRMOVQ) {
        if (Cnd) dstE = rB;
    } 
    // 情况 B: 立即数加载 (irmovq) 或 算术运算 (OPq)
    else if (icode == I_IRMOVQ || icode == I_OPQ) {
        dstE = rB;
    }
    // 情况 C: 栈操作 (push, pop, call, ret)
    // 这些指令全都会修改 %rsp，结果都在 valE 里
    else if (icode == I_PUSHQ || icode == I_POPQ || icode == I_CALL || icode == I_RET) {
        dstE = REG_RSP; 
    }

    // ==========================================================
    // 2. 确定 dstM
    //    valM 来自内存读取 (mrmovq, pop, ret)
    // ==========================================================
    byte_t dstM = REG_NONE;

    // 情况 A: 读内存 (mrmovq)
    if (icode == I_MRMOVQ) {
        dstM = rA; 
    }
    // 情况 B: 弹栈 (popq)
    // popq rA  ->  valM = Memory[%rsp]  -> 写入 rA
    else if (icode == I_POPQ) {
        dstM = rA; 
    }

    // ==========================================================
    // 3. 执行写入 (Update Register File)
    // ==========================================================
    
    // 先写 valE
    if (dstE != REG_NONE) {
        reg[dstE] = valE;
    }

    // 后写 valM
    
    if (dstM != REG_NONE) {
        reg[dstM] = valM;
    }
}

int main()
{
    return 0;
}