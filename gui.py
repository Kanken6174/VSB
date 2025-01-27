# gui.py
import tkinter as tk
from tkinter import messagebox

from parser import find_blocks
from gui_components import EntityBlock, AdapterBlock
from generator import generate_top_level

def run_gui(directory):
    blocks = find_blocks(directory)

    root = tk.Tk()
    root.title("Efinix System Builder")

    left_frame = tk.Frame(root)
    left_frame.pack(side="left", fill="y", padx=5, pady=5)

    tk.Label(left_frame, text="Available Blocks").pack()

    blocks_listbox = tk.Listbox(left_frame)
    blocks_listbox.pack(fill="both", expand=True)

    for block in blocks:
        name, generics, ports = block
        if generics == [] and ports == []:
            block_type = "Empty Block"
        elif generics == [] and ports:
            block_type = "Entity/Component"
        else:
            block_type = "Entity/Component"
        blocks_listbox.insert("end", f"{block_type}: {name}")

    add_conduit_button = tk.Button(left_frame, text="New Conduit", command=lambda: add_conduit(root, canvas))
    add_conduit_button.pack(pady=5, fill="x")

    generate_button = tk.Button(left_frame, text="Generate TopLevel", command=lambda: generate_top_level(canvas))
    generate_button.pack(pady=5, fill="x")

    right_frame = tk.Frame(root)
    right_frame.pack(side="right", expand=True, fill="both")

    canvas = tk.Canvas(right_frame, bg="white")
    canvas.pack(expand=True, fill="both")

    canvas.data = {
        "connections": [],
        "blocks": [],
        "port_map": {},
        "active_line": None,
        "active_port": None
    }

    def start_drag(event):
        selection = blocks_listbox.curselection()
        if selection:
            index = selection[0]
            item = blocks_listbox.get(index)
            block_info = item.split(": ")
            if len(block_info) == 2:
                block_type, block_name = block_info
                selected_block = next((b for b in blocks if b[0] == block_name), None)
                if selected_block:
                    canvas.data["drag_block"] = selected_block
                    canvas.data["drag_label"] = tk.Label(left_frame, text=block_name, bg="lightgreen")
                    canvas.data["drag_label"].place(x=event.x, y=event.y)
                    blocks_listbox.bind("<Motion>", on_drag_motion)
                    blocks_listbox.bind("<ButtonRelease-1>", on_drag_release)

    def on_drag_motion(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].place(x=event.x, y=event.y)

    def on_drag_release(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].destroy()
            del canvas.data["drag_label"]
            block = canvas.data.get("drag_block")
            if block:
                canvas_x = canvas.winfo_pointerx() - canvas.winfo_rootx() - right_frame.winfo_x()
                canvas_y = canvas.winfo_pointery() - canvas.winfo_rooty() - right_frame.winfo_y()
                if 0 <= canvas_x <= canvas.winfo_width() and 0 <= canvas_y <= canvas.winfo_height():
                    name, generics, ports = block
                    if generics == [] and ports == []:
                        messagebox.showinfo("Info", f"Block '{name}' has no generics or ports.")
                    elif generics == [] and ports:
                        block_instance = EntityBlock(canvas, canvas_x, canvas_y, name, generics, ports, conduit=False)
                        canvas.data["blocks"].append(block_instance)
                    else:
                        block_instance = EntityBlock(canvas, canvas_x, canvas_y, name, generics, ports, conduit=False)
                        canvas.data["blocks"].append(block_instance)
            del canvas.data["drag_block"]
            blocks_listbox.unbind("<Motion>")
            blocks_listbox.unbind("<ButtonRelease-1>")

    blocks_listbox.bind("<Button-1>", start_drag)

    def add_conduit(root, canvas):
        conduit_window = tk.Toplevel(root)
        conduit_window.title("New Conduit")

        tk.Label(conduit_window, text="Name:").pack(pady=2)
        name_entry = tk.Entry(conduit_window)
        name_entry.insert(0, "sig")
        name_entry.pack(pady=2)

        tk.Label(conduit_window, text="Direction:").pack(pady=2)
        direction_var = tk.StringVar(conduit_window, "in")
        tk.OptionMenu(conduit_window, direction_var, "in", "out", "inout").pack(pady=2)

        tk.Label(conduit_window, text="Bit width (leave blank for default):").pack(pady=2)
        width_entry = tk.Entry(conduit_window)
        width_entry.insert(0, "1")
        width_entry.pack(pady=2)

        tk.Label(conduit_window, text="Base Type (e.g., std_logic, integer):").pack(pady=2)
        type_entry = tk.Entry(conduit_window)
        type_entry.insert(0, "std_logic")
        type_entry.pack(pady=2)

        def create_conduit():
            name = name_entry.get().strip()
            direction = direction_var.get()
            width = width_entry.get().strip()
            base_type = type_entry.get().strip()

            if not name:
                messagebox.showerror("Input Error", "Conduit name cannot be empty.")
                return

            for block in canvas.data["blocks"]:
                if hasattr(block, 'conduit') and block.conduit and block.name == name:
                    messagebox.showerror("Duplicate Error", f"Conduit '{name}' already exists.")
                    return

            if width.isdigit():
                width = int(width)
                if width <= 1:
                    if base_type.lower() in ["std_logic_vector", "signed", "unsigned", "std_logic"]:
                        final_type = "std_logic"
                    else:
                        final_type = base_type
                else:
                    if base_type.lower() == "std_logic":
                        final_type = f"std_logic_vector({width-1}:0)"
                    elif base_type.lower() in ["signed", "unsigned", "std_logic_vector"]:
                        final_type = f"{base_type}({width-1}:0)"
                    else:
                        final_type = base_type
            else:
                final_type = base_type

            conduit = EntityBlock(canvas, 100, 100, name, generics=[], ports=[{"name": name, "dir": direction, "type": final_type}], conduit=True)
            canvas.data["blocks"].append(conduit)
            conduit_window.destroy()

        tk.Button(conduit_window, text="Create", command=create_conduit).pack(pady=10)

    root.mainloop()
