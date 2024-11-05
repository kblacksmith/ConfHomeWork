import re
import json
from dict2xml import dict2xml
import sys

def parse_array(value: str):
    array_values = []
    nested_level = 0
    current_value = ""

    for char in value[1:-1]:  # Убираем внешние скобки {}
        if char == '{' or char == '[':
            nested_level += 1
            current_value += char
        elif char == '}' or char == ']':
            nested_level -= 1
            current_value += char
        elif char == ',' and nested_level == 0:
            array_values.append(parse_value(current_value.strip()))
            current_value = ""
        else:
            current_value += char

    if current_value:
        array_values.append(parse_value(current_value.strip()))

    return array_values

def parse_dict(value: str):
    dict_values = {}
    nested_level = 0
    key = ""
    current_value = ""
    is_key = True

    for char in value[2:-2]:  # Убираем внешние скобки ([ ])
        if char == '{' or char == '[':
            nested_level += 1
            current_value += char
        elif char == '}' or char == ']':
            nested_level -= 1
            current_value += char
        elif char == ',' and nested_level == 0:
            if is_key:
                key = current_value.strip()
                is_key = False
            else:
                dict_values[key] = parse_value(current_value.strip())
                is_key = True
            current_value = ""
        elif char == ':' and nested_level == 0 and is_key:
            key = current_value.strip()
            current_value = ""
            is_key = False
        else:
            current_value += char

    if key and current_value:
        dict_values[key.strip()] = parse_value(current_value.strip())

    return dict_values

def parse_value(value: str):
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        return parse_array(value)
    if value == "([":  # Пустой словарь
        return {}
    if value.isdigit():
        return int(value)
    if value.startswith("([") and value.endswith("])"):
        return parse_dict(value)
    if re.match(r'\$"[_a-zA-Z1-90!#%^&*()]*"', value):
        return value[2:-1]
    return value

def parse_comment(line: str):
    if line.startswith("-- "):
        return line[3:].strip()
    elif line.startswith("#|"):
        return line[2:].strip()
    return None

def parser(inp: str):
    inp = inp.replace("const", "")
    inp = inp.split(' : ', 1)
    key = inp[0].strip()
    value_str = inp[1].strip()
    #обработка запятой в конце строки
    if value_str[-1] == ",":
        value_str = value_str[:-1]

    value = parse_value(value_str)
    return key, value

def main():
    if len(sys.argv) < 2:
        print("Укажите путь к файлу конфигурации .conf")
        return

    file_path = sys.argv[1]

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            comcounter = 0
            all_ = {}
            root = all_
            comments = []
            multiline_comment = False
            for line in file:
                line = line.strip()
                if line == '__stop__':
                    break
                elif line == '])':
                    root = all_
                elif line.startswith("#|"):
                    multiline_comment = True
                    #comments.append(parse_comment(line))
                elif line.endswith("|#") and multiline_comment:
                    multiline_comment = False
                    #comments.append(line[:-2].strip())
                elif line.startswith("-- ") and not multiline_comment:
                    comments.append(parse_comment(line))
                    comcounter+=1
                    root["comment"+str(comcounter)] = line[3:]
                elif multiline_comment:
                    comments.append(line)
                    root["comment" + str(comcounter)] = line
                    comcounter+=1
                elif not multiline_comment:
                    match = re.match(r"\$[_a-zA-Z]+\$", line)
                    if match and match.endpos == len(line):
                        if line[1:-1] in root.keys():
                            print(root[line[1:-1]])
                        else:
                            print("error not in memory")
                    else:
                        try:
                            key, var = parser(line)
                            root[key] = var
                            if var == {}:
                                root = root[key]
                        except Exception as e:
                            print(e)

            # Добавление комментариев в результирующий словарь
            #if comments:
                #root["comments"] = comments
            # Печать результата в формате XML
            #print(root)
            xml = dict2xml(root)
            xml = re.sub(r'</comment\d+>', '-->', xml)
            xml = re.sub(r'<comment\d+>', '<!--', xml)
            print(xml)

    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")

if __name__ == '__main__':
    main()
