import csv
import sys
class Assembler:
    def __init__(self, path_to_programm: str, path_to_binary: str, path_to_log_file):
        self.FREE_MEMORY_ADDRESS = -1
        self.NAMESPACE = {}
        self.INPUT_FILE = path_to_programm
        self.OUTPUT_FILE = path_to_binary
        self.LOG_FILE = path_to_log_file
        open(self.OUTPUT_FILE, 'w').close()
        open(self.LOG_FILE, 'w').close()

        self.LOG_ARRAY = []

    def get_free_address(self):
        self.FREE_MEMORY_ADDRESS += 1
        return self.FREE_MEMORY_ADDRESS

    def add_var_to_namespace(self, var: str) -> int:
        ADDRESS = self.get_free_address()
        self.NAMESPACE[var] = ADDRESS
        return ADDRESS

    def write_to_binary(self, bytes: bytes):
        logged = ", ".join([("0x" + hex(i)[2:].zfill(2).upper()).ljust(4, '0') for i in bytes])
        self.log({"bin": logged}, method="append")

        with open(self.OUTPUT_FILE, 'ab') as f:
            f.write(bytes)

    def bit_inp(self, a: int, b: int, c: int, d: int = 0):
        if d:
            self.log({"A": a, "B": b, "C": c, "D": d})
            a = bin(a)[2:].zfill(7)
            b = bin(b)[2:].zfill(11)
            c = bin(c)[2:].zfill(11)
            d = bin(d)[2:].zfill(15)
            s = d + c + b + a
        else:
            self.log({"A": a, "B": b, "C": c})
            a = bin(a)[2:].zfill(7)
            b = bin(b)[2:].zfill(11)
            c = bin(c)[2:].zfill(12)
            s = c + b + a
        s = s.zfill(48)
        return int(s, 2).to_bytes(6, "big")[::-1]

    def log(self, text: dict, method="last"):
        if method == "last":
            self.LOG_ARRAY.append(text)
        elif method == "append":
            self.LOG_ARRAY[-1].update(text)

    def dump_log(self):
        all_keys = set()
        for entry in self.LOG_ARRAY:
            all_keys.update(entry.keys())
        fieldnames = sorted(all_keys)

        with open(self.LOG_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if f.tell() == 0:
                writer.writeheader()

            writer.writerows(self.LOG_ARRAY)

    def run(self):
        with open(self.INPUT_FILE, 'r') as f:
            lines = f.readlines()
        for line in lines:
            # Загрузка константы
            if line.startswith("set"):
                _, var, value = line.split()
                var, value = var.strip(), int(value.strip())

                address = self.add_var_to_namespace(var)
                binary = self.bit_inp(45, address, value)
                self.write_to_binary(binary)

            # Чтение и запись в памяти
            elif line.startswith("read"):
                _, var1, var2, shift = line.split()
                var1, var2, shift = var1.strip(), var2.strip(), int(shift.strip())

                if var2 not in self.NAMESPACE.keys():
                    raise Exception(f"Переменная '{var2}' не была объявлена.")

                if var1 not in self.NAMESPACE.keys():
                    address1 = self.add_var_to_namespace(var1)
                else:
                    address1 = self.NAMESPACE[var1]
                address2 = self.NAMESPACE[var2]

                binary = self.bit_inp(80, address1, address2, shift)
                self.write_to_binary(binary)

            # Чтение из памяти и запись по адресу со сдвигом
            elif line.startswith("write"):
                _, var1, var2 = line.split()
                var1, var2 = var1.strip(), var2.strip()

                if var1 not in self.NAMESPACE.keys():
                    raise Exception(f"Переменная '{var2}' не была объявлена.")
                if var2 not in self.NAMESPACE.keys():
                    address2 = self.add_var_to_namespace(var2)
                else:
                    address2 = self.NAMESPACE[var2]

                address1 = self.NAMESPACE[var1]
                binary = self.bit_inp(85, address1, address2)
                self.write_to_binary(binary)

            # Унарная операция bitreverse
            elif line.startswith("bswap"):
                _, var1, var2 = line.split()
                var1, var2 = var1.strip(), var2.strip()

                if var2 not in self.NAMESPACE.keys():
                    raise Exception(f"Переменная '{var2}' не была объявлена.")
                if var1 not in self.NAMESPACE.keys():
                    address1 = self.add_var_to_namespace(var1)
                else:
                    address1 = self.NAMESPACE[var1]

                address2 = self.NAMESPACE[var2]
                binary = self.bit_inp(40, address1, address2)
                self.write_to_binary(binary)
        self.dump_log()

class Interpreter:
    def __init__(self, path_to_binary: str, path_to_result):
        with open(path_to_binary, 'rb') as f:
            self.BINARY = f.read()
        self.MEMORY = [0 for _ in range(16)]
        self.RESULT_FILE = path_to_result
        open(self.RESULT_FILE, 'w').close()

    def run(self):
        # Перевод бинарных данных в строку битов
        bits = ''.join(
            ''.join(f"{byte:08b}" for byte in self.BINARY[i:i + 6][::-1])
            for i in range(0, len(self.BINARY), 6)
        )

        # Разделение на команды длиной 48 бит (6 байт)
        commands = [bits[i:i + 48] for i in range(0, len(bits), 48)]

        for command in commands:
            command_type = command[-7:]
            if command_type == "0101101":  # set
                address = int(command[-18:-7], 2)
                value = int(command[-29:-18], 2)
                self.MEMORY[address] = value


            elif command_type == "1010000":  # read
                address1 = int(command[-18:-7], 2)
                address2 = int(command[-29:-18], 2)
                value = self.MEMORY[address2]
                shift = int(command[:-29], 2)
                self.MEMORY[address1] = self.MEMORY[value  + shift]

            elif command_type == "1010101":  # write
                address1 = int(command[-18:-7], 2)
                address2 = int(command[-29:-18], 2)
                self.MEMORY[address2] = self.MEMORY[address1]

            elif command_type == "0101000":  # bswap
                address1 = int(command[-18:-7], 2)
                address2 = int(command[-29:-18], 2)
                value = self.MEMORY[address2]
                swapped_value = (
                    ((value & 0xFF000000) >> 24) |
                    ((value & 0x00FF0000) >> 8) |
                    ((value & 0x0000FF00) << 8) |
                    ((value & 0x000000FF) << 24)
                )
                self.MEMORY[address1] = swapped_value

        self.log_result()


    def log_result(self):
        # Создаем список для записи в CSV
        data = []

        for i, value in enumerate(self.MEMORY):
            data.append({"0b" + bin(i)[2:].zfill(4): value})
        all_keys = set()
        for entry in data:
            all_keys.update(entry.keys())

        with open(self.RESULT_FILE, 'w', newline='') as f:
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

    assembler = Assembler(programm_file, binary_file, log_file)
    assembler.run()

    interpreter = Interpreter(binary_file, "result.csv")
    interpreter.run()


if __name__ == '__main__':
    main()
