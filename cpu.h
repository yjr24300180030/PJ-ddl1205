include "y86_defs.h"
class Simulator
{
public:
    Simulator();

    void loadProgram();//done

    int fetch();//done

    int decode();//done

    void pc_update();//done

    // 写回：将 valE 或 valM 写回 reg
    void write_back();//done

    void memory_access();//done

    void execute();
    // 处理小端序读写内存 (比如读8个字节拼成一个 int64)
    word_t readMemoryWord(addr_t addr, bool& error);//done

    void writeMemoryWord(addr_t addr, word_t val, bool& error);//done

    void run();
    
    bool check_condition(int ifun, bool zf, bool sf, bool of);//done

private:
    addr_t PC = 0;              // 程序计数器
    word_t reg[15];             // 寄存器文件
    std::map<addr_t, byte_t> memory; // 内存
    ConditionCodes cc;          // 条件码 (ZF, SF, OF)
    Stat stat = STAT_AOK;       // 系统状态

    // ==========================================
    // 2. 阶段中间值 (Stage Latches)
    // 这些变量用于在 fetch, decode, execute 之间传递数据
    // ==========================================
    byte_t icode, ifun; // 取指阶段读出的指令码和功能码
    byte_t rA, rB;      // 寄存器索引
    word_t valC;        // 8字节立即数
    word_t valP;        // 下一条指令地址 (PC + length)
    
    word_t valA, valB;  // 译码阶段读出的寄存器值
    word_t valE;        // 执行阶段 ALU 计算结果
    word_t valM;        // 访存阶段读出的内存值
    bool Cnd;             // 跳转/传送条件 (execute 计算, write_back 使用)


};