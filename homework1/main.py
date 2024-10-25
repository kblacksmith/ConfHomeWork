import zipfile
from datetime import datetime
import yaml
import tkinter as tk

history = []
path = ['archive']
directory = []
all_f = []


def clear():
    global history, all_f, path, directory
    history = []
    all_f = []
    #path = ['archive']
    directory = []


def add_to_history(user, command, param):
    action = {
        "user": user,
        "command": command,
        "param": param,
        "time": str(datetime.now())
    }
    history.append(action)


def find_file(text):
    global path, directory
    if text[0] == '/':
        path_new = path + text[1:].split('/')
    else:
        path_new = text.split('/')
    for elem in directory:
        if elem == path_new:
            return elem
    return None


def rep(x):
    if x[-1] == '/':
        return x.split('/')[:-1]
    return x.split('/')


def head_file(archive, filepath, num_lines=10):
    """Reads the first `num_lines` of a file from the zip archive."""
    try:
        with archive.open(filepath, 'r') as file:
            content = ""
            for i, line in enumerate(file):
                if i >= num_lines:
                    break
                content += line.decode().strip() + "\n"
            return content[:-1]
    except KeyError:
        return f"File '{filepath}' not found in archive."
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"


def process_command(command_line, text_area):
    global path
    with open('konf.yaml') as f:
        templates = yaml.safe_load(f)

    files = templates['path_vm'] + "\\archive.zip"
    user = templates['user']
    computer = templates['computer']
    with zipfile.ZipFile(files) as zf:
        for der in sorted(map(rep, zf.namelist()), key=lambda x: len(x)):
            directory.append(der)
        if not command_line.strip():
            return

        try:
            command, *param = command_line.split()
        except ValueError:
            return

        add_to_history(user, command, param)
        output = ""

        if command == "ls":
            current_dir = '/'.join(path)
            content = [d[-1] for d in directory if d[:-1] == path]
            if content:
                output = "\n".join(content)
            else:
                output = f"No files in directory '{current_dir}'"

        elif command == "cd":
            if len(param) == 0:
                output = "You need to specify a directory"
            else:
                file = find_file(param[0])
                if file is None:
                    output = f"Path '{param[0]}' does not exist."
                else:
                    path = file
                    output = f"Changed directory to '{'/'.join(path)}'"

        elif command == "head":
            if len(param) == 0:
                output = "You need to specify a file."
            else:
                filepath = '/'.join(path + [param[0]])
                num_lines = int(param[1]) if len(param) > 1 else 10
                output = head_file(zf, filepath, num_lines)

        elif command == "history":
            output = "\n".join([f"{action['time']} {action['user']} {action['command']} {action['param']}" for action in history])

        elif command == "exit":
            clear()
            text_area.insert(tk.END, "Exiting...\n")
            text_area.master.quit()

        else:
            output = f"The name '{command}' is not recognized as a command name"

        text_area.insert(tk.END, "\n" + output)
    clear()



def create_shell_gui():
    window = tk.Tk()
    window.title("Shell Emulator")

    # Text area for displaying shell session
    text_area = tk.Text(window, height=30, width=100, bg='black', fg='white', insertbackground='white')
    text_area.pack()

    global path
    with open('konf.yaml') as f:
        templates = yaml.safe_load(f)

    files = templates['path_vm'] + "\\archive.zip"
    user = templates['user']
    computer = templates['computer']
    text_area.insert(tk.END, f"[{user}@{computer}] : {'/'.join(path)} $ ")

    # Handle user input
    def on_enter(event):
        # Get the command after the last prompt
        command_line = text_area.get("end-2l linestart", "end-1c")[::-1]
        redcom = ""
        for i in command_line:
            if i != "$":
                redcom += i
            else: break
        redcom = redcom[::-1]
        if command_line:
            process_command(redcom, text_area)
        text_area.insert(tk.END, f"\n[{user}@{computer}] : {'/'.join(path)} $ ")

        text_area.see(tk.END)

        return "break"

    text_area.bind("<Return>", on_enter)

    window.mainloop()


if __name__ == '__main__':
    create_shell_gui()
