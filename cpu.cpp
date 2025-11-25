#include "cpu.h"
#include <fstream>
void Simulator::fetch() {
    // 初始化 fetch 阶段产生的信号
    bool imem_error = false; 

    // ---------------------------------------------------------
    // 1. 读取第一个字节 (icode:ifun)
    // ---------------------------------------------------------
    if (memory.find(PC) == memory.end() && PC >= MEM_MAX_SIZE) {
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

int main()
{
    return 0;
}