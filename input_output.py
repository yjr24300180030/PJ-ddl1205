#!/usr/bin/env python3
import sys
import os
import json
import hashlib
import subprocess
import tempfile
from typing import Dict, List, Optional

MEM_MAX_SIZE: int = 0x20000

def parse_yo_stream(stream: List[str]) -> Dict[int, int]:
    memory: Dict[int, int] = {}
    for line in stream:
        s = line.rstrip()
        if not s or ":" not in s: continue
        if '|' in s: s = s.split('|', 1)[0]
        s = s.strip()
        if not s: continue
        try:
            addr_str, hex_str = s.split(':', 1)
            hex_str = hex_str.strip().replace(' ', '')
            if not hex_str: continue
            base_addr = int(addr_str, 16)
            if base_addr >= MEM_MAX_SIZE: continue
            if len(hex_str) % 2 == 1: hex_str += '0'
            for i in range(0, len(hex_str), 2):
                byte_val = int(hex_str[i:i+2], 16)
                if base_addr + (i//2) < MEM_MAX_SIZE:
                    memory[base_addr + (i//2)] = byte_val & 0xFF
        except ValueError: continue
    return memory

def run_cpp_simulator(memory: Dict[int, int]) -> Optional[list]:
    # 自动定位 cpu 或 cpu.exe
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(base_dir, 'cpu')
    if not (os.path.isfile(exe_path) and os.access(exe_path, os.X_OK)):
        exe_path += ".exe"
        
    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
            for addr, byte_val in sorted(memory.items()):
                tmp.write(f"{addr} {byte_val:02X}\n")
            tmp_name = tmp.name
            
        # 这里的 timeout 设为 5 秒，防止 C++ 死循环卡死
        proc = subprocess.run([exe_path, tmp_name], capture_output=True, text=True, check=True, timeout=5)
        return json.loads(proc.stdout)
    except Exception:
        return None
    finally:
        if tmp_name and os.path.exists(tmp_name):
            try: os.unlink(tmp_name)
            except OSError: pass

def simulate_program(lines: List[str]) -> List:
    # 1. 解析
    mem = parse_yo_stream(lines)
    
    # 2. 运行 C++
    res = run_cpp_simulator(mem)
    
    if res is None: 
        raise RuntimeError("Simulator failed")
    
    res = clean_memory_zeros(res)

    return res
def clean_memory_zeros(data: List[dict]) -> List[dict]:
    """
    遍历结果列表，删除 MEM 中所有值为 0 的项
    以匹配标准答案的稀疏表示法
    """
    for step in data:
        if 'MEM' in step and isinstance(step['MEM'], dict):
            step['MEM'] = {k: v for k, v in step['MEM'].items() if v != 0}
    return data

def main():
    # 纯净的入口：只读 stdin，只写 stdout
    try:
        content = sys.stdin.read()
        if not content: return
        result = simulate_program(content.splitlines())
        json.dump(result, sys.stdout, indent=4)
    except Exception:
        sys.exit(1)

if __name__ == '__main__':
    main()
