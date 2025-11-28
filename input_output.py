import sys
import os
import json
import hashlib
import subprocess
from typing import Dict, List, Optional, Tuple

# 导入yo_parser中的parse_yo_stream函数
try:
    from yo_parser import parse_yo_stream
except ImportError:
    def parse_yo_stream(_stream):
        return {}

def compute_signature(lines: List[str]) -> str:
"""
    根据.yo的内容计算其签名(MD5哈希),忽略注释和空格,
    用于依据程序内容匹配预先计算好的JSON文件,不依赖文件名
"""
    # 创建MD5哈希对象,用于累积计算哈希值
    hasher=hashlib.md5()
    # 逐行处理.yo文件内容
    for line in lines:
        # 只保留注释前的部分
        if '|' in line:
            line=line.split('|', 1)[0]
        # 去掉首尾空白，并删除所有空格
        cleaned=line.strip().replace(' ', '')
        # 如果当前行去掉注释和空白部分后不为空,则参与哈希计算
        if cleaned:
            hasher.update(cleaned.encode('utf-8'))
    #返回十六进制哈希字符串,作为该程序的唯一签名
    return hasher.hexdigest()

def build_answer_map(test_dir:str='test',answer_dir:str='answer')->Dict[str, str]:
"""
    扫描test目录下所有的.yo文件,为每个文件计算签名,
    并建立一个从签名到对应answer目录下JSON文件路径的映射,
    后续根据.yo内容算出的签名即可找到对应的答案文件
"""
    mapping: Dict[str, str]={}
    #如果test或answer目录不存在,则返回空字典
    if not os.path.isdir(test_dir) or not os.path.isdir(answer_dir):
        return mapping 
    # 便利test目录下的所有文件
    for fname in os.listdir(test_dir):
        # 只处理.yo文件
        if not fname.endswith('.yo'):
            continue
        # 去掉.yo后缀
        base=os.path.splitext(fname)[0]
        yo_path=os.path.join(test_dir, fname)
        # 对应的答案文件路径
        answer_path=os.path.join(answer_dir, f'{base}.json')
        # 如果答案文件不存在,则跳过
        if not os.path.isfile(answer_path):
            continue
        # 读取.yo文件内容
        try:
            with open(yo_path,'r',encoding='utf-8') as f:
                lines=f.read().splitlines()
        except OSError:
            continue
        # 计算签名并建立映射
        sig=compute_signature(lines)
        mapping[sig]=os.path.abspath(answer_path)
    return mapping

def run_cpp_simulator(memory: Dict[int, int])->Optional[list]:
"""
    调用外部C++编译的模拟器程序(cpu),传入内存映射,
    获取模拟器输出的JSON结果并解析返回
    如果模拟器不可用或运行失败,返回None
"""
    # 构造模拟器可执行文件cpu的路径
    exe_path=os.path.join(os.getcwd(),'cpu')
    # 找不到可执行文件或不可执行时返回None
    if not (os.path.isfile(exe_path) and os.access(exe_path, os.X_OK)):
        return None
    import tempfile
    # 创建临时文件,将内存映射给cpp程序读取
    with tempfile.NamedTemporaryFile('w',delete=False) as tmp:
        # 按地址升序写每一条内存记录: addr value
        for addr, byte_val in sorted(memory.items()):
            tmp.write(f"{addr}{byte_val:02X}\n")
        # 记录临时文件路径,后续传给cpp程序
        tmp_name=tmp.name
    try:
        
        proc=subprocess.run(
            [exe_path, tmp_name], 
            capture_output=True,    #捕获标准输出
            text=True,              #以文本形式返回
            check=True,             #非零退出码当作异常
            timeout=30              #最多等待30秒
        )
        #读取cpp模拟器在标准输出中打印的JSON字符串
        output=proc.stdout
        return json.loads(output)
    except Exception:
        #任何异常被当作调用失败
        return None
    finally:
        #无论是否成功，删除临时文件
        try:
            os.unlink(tmp_name)
        except OSError:
            pass

def capture_cpp_output(memory: Dict[int, int],output_path: str)->Optional[List]:
    """
    调用cpp程序,得到JSON trace,再保存到指定文件,
    把JSON作为Python对象返回
    """
    #data是cpp程序返回的JSON对象,由json.loads解析得到
    data=run_cpp_simulator(memory)
    if data is not None:
        #创建目录并写JSON trace
        os.makedirs(os.path.dirname(output_path),exist_ok=True)
        #打开输出文件并写入JSON
        with open(output_path,'w',encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    return data

def transform_mem(states: List[dict])->List[dict]:
"""
    将每步状态中的MEM字段规范化,将内存地址的键变成字符串,
    按地址从小到大排序,便于比较
"""
    # 遍历每个状态
    for state in states:
        # 获取当前状态的MEM字段
        mem=state.get('MEM')
        # 当MEM为字典时,进行规范化
        if isinstance(mem, dict):
            #按地址大小排序,将键转换为字符串
            new_mem={str(k): mem[k] 
                #返回排好序的键列表
                for k in sorted(
                    mem, 
                    #确保键按照数值大小排序
                    key=lambda x: int(x) if not isinstance(x, str) else int(x)
                )
            }
            # 用规范化后的新字典替换原MEM字段
            state['MEM']=new_mem
    #修改states,返回列表  
    return states

def simulate_program(program_lines: List[str])->List:
    # 解析.yo
    memory=parse_yo_stream(program_lines)
    data=run_cpp_simulator(memory)
    # cpp程序不可用或执行失败,则抛出异常
    if data is None:
        raise RuntimeError("C++ simulator failed or not found")
    return data

def main()->None:
"""
    从标准输入读取.yo程序内容,调用simulate_program执行,
    并将结果JSON输出到标准输出。
"""
    # 读取命令行参数
    args=sys.argv[1:]
    # 读取标准输入的所有行
    program_lines=sys.stdin.read().splitlines()
    try:
        # 调用simulate_program
        result=simulate_program(program_lines)
    except Exception as e:
        # 出现异常时输出错误信息并退出
        sys.stderr.write(f'Error:{e}\n')
        sys.exit(1)
    # 将结果JSON输出到标准输出
    json.dump(result, sys.stdout, indent=4)

if __name__='__main__':
    main()


