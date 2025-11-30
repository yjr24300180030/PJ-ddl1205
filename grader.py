import os
import json
import sys
# 引入你之前修好的 input_output.py 中的核心函数
try:
    from input_output import simulate_program
except ImportError:
    print("Error: 找不到 input_output.py，请确保它在同一目录下。")
    sys.exit(1)

# 配置颜色输出，看着更清晰
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def load_json_file(filepath):
    """读取 JSON 文件"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Colors.RED}无法读取参考答案 {filepath}: {e}{Colors.RESET}")
        return None

def compare_state(step_idx, actual, expected):
    """比较单个步骤的状态"""
    errors = []

    # 1. 比较 PC
    if actual.get("PC") != expected.get("PC"):
        errors.append(f"PC mismatch: Yours={actual.get('PC')}, Expected={expected.get('PC')}")

    # 2. 比较 STAT
    if actual.get("STAT") != expected.get("STAT"):
        errors.append(f"STAT mismatch: Yours={actual.get('STAT')}, Expected={expected.get('STAT')}")

    # 3. 比较 CC (条件码)
    # 处理可能的 null 或缺失情况
    act_cc = actual.get("CC", {})
    exp_cc = expected.get("CC", {})
    if act_cc != exp_cc:
        errors.append(f"CC mismatch: Yours={act_cc}, Expected={exp_cc}")

    # 4. 比较 REG (寄存器)
    act_reg = actual.get("REG", {})
    exp_reg = expected.get("REG", {})
    # 找出所有涉及的寄存器名
    all_regs = set(act_reg.keys()) | set(exp_reg.keys())
    for r in all_regs:
        v1 = act_reg.get(r, 0)
        v2 = exp_reg.get(r, 0)
        if v1 != v2:
            errors.append(f"Reg {r} mismatch: Yours={v1}, Expected={v2}")

    # 5. 比较 MEM (内存)
    act_mem = actual.get("MEM", {})
    exp_mem = expected.get("MEM", {})
    
    # 内存比较稍微麻烦点，因为 key 可能是字符串 "0"
    # 我们把所有 key 转成 int 进行比较，把 value 也对比
    act_mem_int = {int(k): v for k, v in act_mem.items()}
    exp_mem_int = {int(k): v for k, v in exp_mem.items()}
    
    all_addrs = set(act_mem_int.keys()) | set(exp_mem_int.keys())
    for addr in all_addrs:
        v1 = act_mem_int.get(addr, 0) # 默认为0
        v2 = exp_mem_int.get(addr, 0)
        if v1 != v2:
            errors.append(f"Mem addr {addr} mismatch: Yours={v1}, Expected={v2}")

    return errors

def run_test(yo_file, answer_file):
    """运行单个测试用例"""
    print(f"Testing {os.path.basename(yo_file)} ... ", end='', flush=True)

    # 1. 获取标准答案
    expected_data = load_json_file(answer_file)
    if expected_data is None:
        print(f"{Colors.YELLOW}SKIP (No Answer){Colors.RESET}")
        return True # 没答案不算错

    # 2. 运行模拟器获取你的输出
    try:
        with open(yo_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        actual_data = simulate_program(lines)
    except Exception as e:
        print(f"{Colors.RED}CRASH{Colors.RESET}")
        print(f"  Simulate Error: {e}")
        return False

    # 3. 比较长度 (步数是否一致)
    if len(actual_data) != len(expected_data):
        print(f"{Colors.RED}FAIL{Colors.RESET}")
        print(f"  Step count mismatch: Yours={len(actual_data)}, Expected={len(expected_data)}")
        return False

    # 4. 逐帧比较
    for i in range(len(expected_data)):
        errors = compare_state(i, actual_data[i], expected_data[i])
        if errors:
            print(f"{Colors.RED}FAIL{Colors.RESET}")
            print(f"  Mismatch at Step {i} (PC={actual_data[i].get('PC')}):")
            for err in errors[:5]: # 最多打印前5个错误，防止刷屏
                print(f"    - {err}")
            return False

    print(f"{Colors.GREEN}PASS{Colors.RESET}")
    return True

def main():
    test_dir = 'test'
    answer_dir = 'answer'

    if not os.path.isdir(test_dir):
        print(f"Error: {test_dir} 目录不存在")
        return

    # 获取所有 .yo 文件并排序
    files = sorted([f for f in os.listdir(test_dir) if f.endswith('.yo')])
    
    if not files:
        print("No .yo files found in test/")
        return

    total = 0
    passed = 0

    print(f"{'='*40}")
    print(f"Starting Grading for {len(files)} files")
    print(f"{'='*40}")

    for f in files:
        yo_path = os.path.join(test_dir, f)
        # 假设答案文件名是 prog1.yo -> prog1.json
        base_name = os.path.splitext(f)[0]
        json_path = os.path.join(answer_dir, f"{base_name}.json")
        
        total += 1
        if run_test(yo_path, json_path):
            passed += 1

    print(f"{'='*40}")
    if passed == total:
        print(f"{Colors.GREEN}All Tests Passed! ({passed}/{total}){Colors.RESET}")
    else:
        print(f"{Colors.RED}Some Tests Failed. ({passed}/{total}){Colors.RESET}")

if __name__ == "__main__":
    main()
