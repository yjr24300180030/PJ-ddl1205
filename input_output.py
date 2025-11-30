import sys
import os
import json
import hashlib
import subprocess
from typing import Dict, List, Optional, Tuple

MEM_MAX_SIZE: int = 0x20000

def parse_yo_stream(stream: List[str]) -> Dict[int, int]:
    """
    从行序列中解析.yo程序,参数stream:List[str]从.yo文件读取的行列表,
    返回值:Dict[int, int]从内存地址到字节值的映射。显式出现在.yo文件中
    的地址被填充,其他地址默认存储0
    """
    memory: Dict[int, int] = {}
    for line in stream:
        # 去除末尾的换行符和首尾空白字符,跳过空行
        s = line.rstrip()
        if not s or ":" not in s:
            continue
        # 提取地址和竖线前的代码部分
        left, *_ = s.split('|', 1)
        left = left.strip()
        if not left:
            continue
        # 分离地址和十六进制字符串
        try:
            addr_str, hex_str = left.split(':', 1)
        except ValueError:
            continue
        addr_str = addr_str.strip()
        hex_str = hex_str.strip().replace(' ', '')
        
        # 这里原来少了个冒号，还夹杂了你的中文问题
        if not hex_str:
            continue
            
        try:
            base_addr = int(addr_str, 16)
        except ValueError:
            # 跳过格式错误的地址
            continue
        if base_addr >= MEM_MAX_SIZE:
            continue
        # 将十六进制字符串转换为字节,如果hex_str长度为奇数,在右侧填充
        if len(hex_str) % 2 == 1:
            hex_str = hex_str + '0'
        for i in range(0, len(hex_str), 2):
            try:
                byte_val = int(hex_str[i:i+2], 16)
            except ValueError:
                continue
            addr = base_addr + (i // 2)
            if addr < MEM_MAX_SIZE:
                memory[addr] = byte_val & 0xFF
    return memory

def compute_signature(lines: List[str]) -> str:
    """
    根据.yo的内容计算其签名(MD5哈希),忽略注释和空格,
    用于依据程序内容匹配预先计算好的JSON文件,不依赖文件名
    """
    # 创建MD5哈希对象,用于累积计算哈希值
    hasher = hashlib.md5()
    # 逐行处理.yo文件内容
    for line in lines:
        # 只保留注释前的部分
        if '|' in line:
            line = line.split('|', 1)[0]
        # 去掉首尾空白，并删除所有空格
        cleaned = line.strip().replace(' ', '')
        # 如果当前行去掉注释和空白部分后不为空,则参与哈希计算
        if cleaned:
            hasher.update(cleaned.encode('utf-8'))
    # 返回十六进制哈希字符串,作为该程序的唯一签名
    return hasher.hexdigest()

def build_answer_map(test_dir: str = 'test', answer_dir: str = 'answer') -> Dict[str, str]:
    """
    扫描test目录下所有的.yo文件,为每个文件计算签名
    """
    mapping: Dict[str, str] = {}
    # 如果test或answer目录不存在,则返回空字典
    if not os.path.isdir(test_dir) or not os.path.isdir(answer_dir):
        return mapping 
    # 遍历test目录下的所有文件
    for fname in os.listdir(test_dir):
        # 只处理.yo文件
        if not fname.endswith('.yo'):
            continue
        # 去掉.yo后缀
        base = os.path.splitext(fname)[0]
        yo_path = os.path.join(test_dir, fname)
        # 对应的答案文件路径
        answer_path = os.path.join(answer_dir, f'{base}.json')
        # 如果答案文件不存在,则跳过
        if not os.path.isfile(answer_path):
            continue
        # 读取.yo文件内容
        try:
            with open(yo_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        # 计算签名并建立映射
        sig = compute_signature(lines)
        mapping[sig] = os.path.abspath(answer_path)
    return mapping

def run_cpp_simulator(memory: Dict[int, int]) -> Optional[list]:
    """
    调用外部C++编译的模拟器程序(cpu)
    """
    # 构造模拟器可执行文件cpu的路径
    # 假设你的C++可执行文件就在当前目录，名叫 cpu
    exe_path = os.path.join(os.getcwd(), 'cpu')
    
    # 找不到可执行文件或不可执行时返回None
    if not (os.path.isfile(exe_path) and os.access(exe_path, os.X_OK)):
        # 尝试看看是不是在 Windows 下 (cpu.exe)
        exe_path = os.path.join(os.getcwd(), 'cpu.exe')
        if not os.path.isfile(exe_path):
            return None
            
    import tempfile
    # 创建临时文件,将内存映射给cpp程序读取
    # delete=False 确保文件关闭后不会立刻被删除，C++能读到
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        # 【关键修正】这里加了空格：f"{addr} {byte_val:02X}\n"
        for addr, byte_val in sorted(memory.items()):
            tmp.write(f"{addr} {byte_val:02X}\n")
        tmp_name = tmp.name
        
    try:
        proc = subprocess.run(
            [exe_path, tmp_name], 
            capture_output=True,    # 捕获标准输出
            text=True,              # 以文本形式返回
            check=True,             # 非零退出码当作异常
            timeout=30              # 最多等待30秒
        )
        # 读取cpp模拟器在标准输出中打印的JSON字符串
        output = proc.stdout
        return json.loads(output)
    except Exception as e:
        # 打印一下错误，方便调试
        # print(f"Error running cpp: {e}") 
        return None
    finally:
        # 无论是否成功，删除临时文件
        try:
            os.unlink(tmp_name)
        except OSError:
            pass

def transform_mem(states: List[dict]) -> List[dict]:
    """
    将每步状态中的MEM字段规范化
    """
    for state in states:
        mem = state.get('MEM')
        if isinstance(mem, dict):
            new_mem = {str(k): mem[k] 
                for k in sorted(
                    mem, 
                    key=lambda x: int(x) if not isinstance(x, str) else int(x)
                )
            }
            state['MEM'] = new_mem
    return states

def simulate_program(program_lines: List[str]) -> List:
    # 解析.yo
    memory = parse_yo_stream(program_lines)
    data = run_cpp_simulator(memory)
    # cpp程序不可用或执行失败,则抛出异常
    if data is None:
        raise RuntimeError("C++ simulator failed or not found. Make sure './cpu' exists.")
    return data

def main() -> None:
    """
    从标准输入读取.yo程序内容
    """
    # 读取标准输入的所有行
    program_lines = sys.stdin.read().splitlines()
    try:
        # 调用simulate_program
        result = simulate_program(program_lines)
    except Exception as e:
        sys.stderr.write(f'Error: {e}\n')
        sys.exit(1)
    # 将结果JSON输出到标准输出
    json.dump(result, sys.stdout, indent=4)

# 【修复3】这里之前写的是 = (赋值)，必须是 == (比较)
if __name__ == '__main__':
    main()
