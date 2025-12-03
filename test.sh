# python test.py --bin ./cpu
# python test.py --bin "python cpu.py"
# or customize your testing command
g++ cpu.cpp -o cpu #先要生成cpu可执行文件（如果没有的话）
python3 test.py --bin "python3 input_output.py"