import csv
import sys

# Глобальные переменные
FREE_MEMORY_ADDRESS = -1
NAMESPACE = {}
LOG_ARRAY = []
OUTPUT_FILE = ""
LOG_FILE = ""


def get_free_address():
    global FREE_MEMORY_ADDRESS
    FREE_MEMORY_ADDRESS += 1
    return FREE_MEMORY_ADDRESS


def add_var_to_namespace(var: str) -> int:
    address = get_free_address()
    NAMESPACE[var] = address
    return address


def write_to_binary(bytes: bytes):
    logged = ", ".join([("0x" + hex(i)[2:].zfill(2).upper()).ljust(4, '0') for i in bytes])
    log({"bin": logged}, method="append")

    with open(OUTPUT_FILE, 'ab') as f:
        f.write(bytes)


def bit_inp(a: int, b: int, c: int, d: int = 0):
    if d:
        log({"A": a, "B": b, "C": c, "D": d})
        a = bin(a)[2:].zfill(7)
        b = bin(b)[2:].zfill(11)
        c = bin(c)[2:].zfill(11)
        d = bin(d)[2:].zfill(15)
        s = d + c + b + a
    else:
        log({"A": a, "B": b, "C": c})
        a = bin(a)[2:].zfill(7)
        b = bin(b)[2:].zfill(11)
        c = bin(c)[2:].zfill(12)
        s = c + b + a
    s = s.zfill(48)
    return int(s, 2).to_bytes(6, "big")[::-1]


def log(text: dict, method="last"):
    if method == "last":
        LOG_ARRAY.append(text)
    elif method == "append":
        LOG_ARRAY[-1].update(text)


def dump_log():
    all_keys = set()
    for entry in LOG_ARRAY:
        all_keys.update(entry.keys())
    fieldnames = sorted(all_keys)

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if f.tell() == 0:
            writer.writeheader()

        writer.writerows(LOG_ARRAY)


def run_assembler(programm_file: str, binary_file: str, log_file: str):
    global OUTPUT_FILE, LOG_FILE
    OUTPUT_FILE = binary_file
    LOG_FILE = log_file

    open(OUTPUT_FILE, 'w').close()
    open(LOG_FILE, 'w').close()

    with open(programm_file, 'r') as f:
        lines = f.readlines()

    for line in lines:
        # Загрузка константы
        if line.startswith("set"):
            _, var, value = line.split()
            var, value = var.strip(), int(value.strip())

            address = add_var_to_namespace(var)
            binary = bit_inp(45, address, value)
            write_to_binary(binary)

        # Чтение и запись в памяти
        elif line.startswith("read"):
            _, var1, var2, shift = line.split()
            var1, var2, shift = var1.strip(), var2.strip(), int(shift.strip())

            if var2 not in NAMESPACE.keys():
                raise Exception(f"Переменная '{var2}' не была объявлена.")

            if var1 not in NAMESPACE.keys():
                address1 = add_var_to_namespace(var1)
            else:
                address1 = NAMESPACE[var1]
            address2 = NAMESPACE[var2]

            binary = bit_inp(80, address1, address2, shift)
            write_to_binary(binary)

        # Чтение из памяти и запись по адресу со сдвигом
        elif line.startswith("write"):
            _, var1, var2 = line.split()
            var1, var2 = var1.strip(), var2.strip()

            if var1 not in NAMESPACE.keys():
                raise Exception(f"Переменная '{var2}' не была объявлена.")
            if var2 not in NAMESPACE.keys():
                address2 = add_var_to_namespace(var2)
            else:
                address2 = NAMESPACE[var2]

            address1 = NAMESPACE[var1]
            binary = bit_inp(85, address1, address2)
            write_to_binary(binary)

        # Унарная операция bitreverse
        elif line.startswith("bswap"):
            _, var1, var2 = line.split()
            var1, var2 = var1.strip(), var2.strip()

            if var2 not in NAMESPACE.keys():
                raise Exception(f"Переменная '{var2}' не была объявлена.")
            if var1 not in NAMESPACE.keys():
                address1 = add_var_to_namespace(var1)
            else:
                address1 = NAMESPACE[var1]

            address2 = NAMESPACE[var2]
            binary = bit_inp(40, address1, address2)
            write_to_binary(binary)

    dump_log()


def run_interpreter(binary_file: str):
    MEMORY = [0 for _ in range(16)]
    RESULT_FILE = "result.csv"
    open(RESULT_FILE, 'w').close()

    with open(binary_file, 'rb') as f:
        BINARY = f.read()

    # Перевод бинарных данных в строку битов
    bits = ''.join(
        ''.join(f"{byte:08b}" for byte in BINARY[i:i + 6][::-1])
        for i in range(0, len(BINARY), 6)
    )

    # Разделение на команды длиной 48 бит (6 байт)
    commands = [bits[i:i + 48] for i in range(0, len(bits), 48)]

    for command in commands:
        command_type = command[-7:]
        if command_type == "0101101":  # set
            address = int(command[-18:-7], 2)
            value = int(command[-29:-18], 2)
            MEMORY[address] = value

        elif command_type == "1010000":  # read
            address1 = int(command[-18:-7], 2)
            address2 = int(command[-29:-18], 2)
            value = MEMORY[address2]
            shift = int(command[:-29], 2)
            MEMORY[address1] = MEMORY[value + shift]

        elif command_type == "1010101":  # write
            address1 = int(command[-18:-7], 2)
            address2 = int(command[-29:-18], 2)
            MEMORY[address2] = MEMORY[address1]

        elif command_type == "0101000":  # bswap
            address1 = int(command[-18:-7], 2)
            address2 = int(command[-29:-18], 2)
            value = MEMORY[address2]
            swapped_value = (
                    ((value & 0xFF000000) >> 24) |
                    ((value & 0x00FF0000) >> 8) |
                    ((value & 0x0000FF00) << 8) |
                    ((value & 0x000000FF) << 24)
            )
            MEMORY[address1] = swapped_value

    log_result(MEMORY)


def log_result(MEMORY):
    # Создаем список для записи в CSV
    data = []

    for i, value in enumerate(MEMORY):
        data.append({"0b" + bin(i)[2:].zfill(4): value})
    all_keys = set()
    for entry in data:
        all_keys.update(entry.keys())

    with open("result.csv", 'w', newline='') as f:
        writer = csv.writer(f)

        for item in data:
            for key, value in item.items():
                writer.writerow([key, value])


def main():
    if len(sys.argv) != 4:
        print("Usage: python your_program.py <programm_file> <binary_file> <log_file>")
        sys.exit(1)
    programm_file = sys.argv[1]
    binary_file = sys.argv[2]
    log_file = sys.argv[3]

    global LOG_FILE
    LOG_FILE = log_file

    run_assembler(programm_file, binary_file, log_file)
    run_interpreter(binary_file)


if __name__ == '__main__':
    main()
