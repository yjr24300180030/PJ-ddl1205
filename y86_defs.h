#ifndef Y86_DEFS_H
#define Y86_DEFS_H

#include <cstdint>

// 1. 类型定义
typedef uint64_t addr_t;
typedef uint64_t word_t; // 对应 Y86 的 8 字节
typedef uint8_t  byte_t; // 对应 1 字节

// 2. 状态码 (Stat)
#define STAT_AOK 1
#define STAT_HLT 2
#define STAT_ADR 3
#define STAT_INS 4

// 3. 寄存器 ID
#define REG_RAX 0
#define REG_RCX 1
#define REG_RDX 2
#define REG_RBX 3
#define REG_RSP 4
#define REG_RBP 5
#define REG_RSI 6
#define REG_RDI 7
#define REG_R8  8
#define REG_R9  9
#define REG_R10 10
#define REG_R11 11
#define REG_R12 12
#define REG_R13 13
#define REG_R14 14
#define REG_NONE 0xF

// 4. 指令编码 (I_CODE)
#define I_HALT   0x0
#define I_NOP    0x1
#define I_RRMOVQ 0x2
#define I_IRMOVQ 0x3
#define I_RMMOVQ 0x4
#define I_MRMOVQ 0x5
#define I_OPQ    0x6
#define I_JXX    0x7
#define I_CALL   0x8
#define I_RET    0x9
#define I_PUSHQ  0xA
#define I_POPQ   0xB

// 5. 功能编码 (F_FUN)
// ALU 运算
#define F_ADD 0x0
#define F_SUB 0x1
#define F_AND 0x2
#define F_XOR 0x3

// 跳转/传送条件 (JXX / CMOVXX)
#define F_JMP 0x0
#define F_JLE 0x1
#define F_JL  0x2
#define F_JE  0x3
#define F_JNE 0x4
#define F_JGE 0x5
#define F_JG  0x6

// 6. 条件码结构体 (CC)
// 注意：我们在 cpu.cpp 里用了小写 zf, sf, of，这里必须匹配！
struct CC {
    bool zf;
    bool sf;
    bool of;
};

// 7. 内存最大大小
#define MEM_MAX_SIZE 0x20000

#endif // Y86_DEFS_H
