#ifndef CPU_H
#define CPU_H

#include "y86_defs.h" // <--- 关键！必须包含这一行
#include <map>
#include <vector>
#include <string>

class Simulator {
public:
    // 构造函数
    Simulator();

    // 核心接口
    void loadProgram(const std::string& filename);
    void run();

private:
    // 硬件状态
    addr_t PC;
    word_t reg[15];          // 寄存器文件
    CC cc;                   // 条件码
    int stat;                // 运行状态
    std::map<addr_t, byte_t> memory; // 内存 (使用 map 稀疏存储)

    // 流水线中间信号 (Pipe Registers)
    byte_t icode, ifun;
    byte_t rA, rB;
    word_t valC;
    word_t valP;
    word_t valA, valB;
    word_t valE, valM;
    bool Cnd;

    // 阶段函数
    void fetch();
    void decode();
    void execute();
    void memory_access();
    void write_back();
    void pc_update();

    // 辅助函数
    word_t readMemoryWord(addr_t addr, bool& error);
    void writeMemoryWord(addr_t addr, word_t val, bool& error);
    bool check_condition(int ifun, bool zf, bool sf, bool of);
    void dumpJson(); // 输出状态
};

#endif // CPU_H
