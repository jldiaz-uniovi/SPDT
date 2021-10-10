import json
import sys

def apply_scale(data_in, scale):
    for v in data_in["values"]:
        v["requests"] *= scale
    return data_in

def main():
    if len(sys.argv) == 1:
        print(f"Uso: {sys.argv[0]} scale < file_in > file_out")
        quit()
    scale = float(sys.argv[1])
    data = sys.stdin.read()
    data_in = json.loads(data)
    data_out = apply_scale(data_in, scale)
    print(json.dumps(data_out))

if __name__ == "__main__":
    main()