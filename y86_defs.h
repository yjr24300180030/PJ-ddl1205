#ifndef Y86_DEFS_H
#define Y86_DEFS_H

#include <cstdint>  
#include <map>      
#include <string>
#include <vector>

// =========================================================
// 1. 基础类型定义 (Base Types)
// =========================================================
// 使用固定宽度的整数，避免不同操作系统下的歧义
typedef int64_t  word_t;  // 表示数据、寄存器值、立即数 (有符号)
typedef uint64_t addr_t;  // 表示内存地址 (无符号)
typedef uint8_t  byte_t;  // 表示单字节 (用于内存存储)

// =========================================================
// 2. 常量定义 (Constants)
// =========================================================
const addr_t MEM_MAX_SIZE = 0x20000; // 假设内存大小，可根据测试用例调整

// =========================================================
// 3. 状态码枚举 (Status Codes)
// 对应 Y86 文档中的 STAT
// =========================================================
enum Stat {
    STAT_AOK = 1, // 正常运行
    STAT_HLT = 2, // 执行了 halt 指令
    STAT_ADR = 3, // 非法地址访问
    STAT_INS = 4  // 非法指令
};

// =========================================================
// 4. 寄存器 ID 枚举 (Register IDs)
// 顺序必须与 Y86 手册一致，也是 JSON 输出数组的索引顺序
// =========================================================
enum RegID {
    REG_RAX = 0,
    REG_RCX = 1,
    REG_RDX = 2,
    REG_RBX = 3,
    REG_RSP = 4,
    REG_RBP = 5,
    REG_RSI = 6,
    REG_RDI = 7,
    REG_R8  = 8,
    REG_R9  = 9,
    REG_R10 = 10,
    REG_R11 = 11,
    REG_R12 = 12,
    REG_R13 = 13,
    REG_R14 = 14,
    REG_NONE= 0xF // 0xF 表示无寄存器 (如 irmovq 的 rA 部分)
};

// =========================================================
// 5. 指令编码枚举 (Instruction Codes)
// 用于 Fetch 和 Decode 阶段的 switch-case
// =========================================================
enum ICode {
    I_HALT   = 0x0,
    I_NOP    = 0x1,
    I_RRMOVQ = 0x2, // 包含 cmovXX
    I_IRMOVQ = 0x3,
    I_RMMOVQ = 0x4,
    I_MRMOVQ = 0x5,
    I_OPQ    = 0x6, // add, sub, and, xor
    I_JXX    = 0x7, // jmp, jle, ...
    I_CALL   = 0x8,
    I_RET    = 0x9,
    I_PUSHQ  = 0xA,
    I_POPQ   = 0xB
};

// 运算指令的功能码 (Function Code for OPq)
enum FunCodeOP {
    F_ADD = 0x0,
    F_SUB = 0x1,
    F_AND = 0x2,
    F_XOR = 0x3
};

// 跳转指令的功能码 (Function Code for Jxx / cmovXX)
enum FunCodeJXX {
    F_JMP = 0x0,
    F_JLE = 0x1,
    F_JL  = 0x2,
    F_JE  = 0x3,
    F_JNE = 0x4,
    F_JGE = 0x5,
    F_JG  = 0x6
};

// =========================================================
// 6. 条件码结构 (Condition Codes)
// 用于保存 ZF, SF, OF
// =========================================================
struct ConditionCodes {
    bool zf = true;  // Zero Flag (默认通常为1或0，视初始化要求定)
    bool sf = false; // Sign Flag
    bool of = false; // Overflow Flag
};

// =========================================================
// 7. 全局系统状态 (System State)
// 这个结构体是 JSON 输出的数据源
// =========================================================
struct SystemState {
    addr_t pc;              // 程序计数器
    word_t reg[15];         // 15个通用寄存器
    ConditionCodes cc;      // 条件码
    Stat stat;              // 运行状态
    

    std::map<addr_t, byte_t> memory; 

    // 构造函数初始化
    SystemState() {
        pc = 0;
        stat = STAT_AOK;
        for(int i=0; i<15; ++i) reg[i] = 0;
    }
};

#endif 
