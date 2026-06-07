import subprocess
import os

cwd = r'c:\Users\carol\Downloads\tr4cking-app\tr4cking'
python_exe = os.path.join(cwd, 'venv', 'Scripts', 'python.exe')
script_path = os.path.join(cwd, 'test_form.py')

print(f"Python path: {python_exe}")
print(f"Script path: {script_path}")

try:
    result = subprocess.run(
        [python_exe, script_path],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15
    )
    
    output = []
    output.append(f"Exit Code: {result.returncode}")
    output.append("=== STDOUT ===")
    output.append(result.stdout)
    output.append("=== STDERR ===")
    output.append(result.stderr)
    
    with open('subprocess_out.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    print("Done executing. Output written to subprocess_out.txt")
except subprocess.TimeoutExpired:
    print("Execution timed out!")
    with open('subprocess_out.txt', 'w', encoding='utf-8') as f:
        f.write("Timed out after 15 seconds")
except Exception as e:
    print(f"Exception: {e}")
    with open('subprocess_out.txt', 'w', encoding='utf-8') as f:
        f.write(f"Exception: {str(e)}")
