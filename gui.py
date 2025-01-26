# gui.py
import tkinter as tk
from tkinter import messagebox

from parser import find_entities
from gui_components import EntityBlock, AdapterBlock
from generator import generate_top_level

def run_gui(directory):
    entities = find_entities(directory)

    root = tk.Tk()
    root.title("Efinix System Builder")

    # Left Frame for Entity List and Controls
    left_frame = tk.Frame(root)
    left_frame.pack(side="left", fill="y", padx=5, pady=5)

    tk.Label(left_frame, text="Available Entities").pack()

    entity_listbox = tk.Listbox(left_frame)
    entity_listbox.pack(fill="both", expand=True)

    for entity in entities:
        entity_listbox.insert("end", entity[0])

    add_conduit_button = tk.Button(left_frame, text="New Conduit", command=lambda: add_conduit(root, canvas))
    add_conduit_button.pack(pady=5, fill="x")

    generate_button = tk.Button(left_frame, text="Generate TopLevel", command=lambda: generate_top_level(canvas))
    generate_button.pack(pady=5, fill="x")

    # Right Frame for Canvas
    right_frame = tk.Frame(root)
    right_frame.pack(side="right", expand=True, fill="both")

    canvas = tk.Canvas(right_frame, bg="white")
    canvas.pack(expand=True, fill="both")

    # Initialize canvas data
    canvas.data = {
        "connections": [],
        "blocks": [],
        "port_map": {},
        "active_line": None,
        "active_port": None
    }

    # Drag and Drop Handlers
    def start_drag(event):
        selection = entity_listbox.curselection()
        if selection:
            index = selection[0]
            entity_name = entity_listbox.get(index)
            entity = next((e for e in entities if e[0] == entity_name), None)
            if entity:
                canvas.data["drag_entity"] = entity
                canvas.data["drag_label"] = tk.Label(left_frame, text=entity_name, bg="lightgreen")
                canvas.data["drag_label"].place(x=event.x, y=event.y)
                entity_listbox.bind("<Motion>", on_drag_motion)
                entity_listbox.bind("<ButtonRelease-1>", on_drag_release)

    def on_drag_motion(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].place(x=event.x, y=event.y)

    def on_drag_release(event):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].destroy()
            del canvas.data["drag_label"]
            entity = canvas.data.get("drag_entity")
            if entity:
                # Get canvas coordinates relative to root window
                canvas_x = canvas.winfo_pointerx() - canvas.winfo_rootx() - right_frame.winfo_x()
                canvas_y = canvas.winfo_pointery() - canvas.winfo_rooty() - right_frame.winfo_y()
                if 0 <= canvas_x <= canvas.winfo_width() and 0 <= canvas_y <= canvas.winfo_height():
                    block = EntityBlock(canvas, canvas_x, canvas_y, entity[0], entity[1], False)
                    canvas.data["blocks"].append(block)
                del canvas.data["drag_entity"]
            entity_listbox.unbind("<Motion>")
            entity_listbox.unbind("<ButtonRelease-1>")

    entity_listbox.bind("<Button-1>", start_drag)

    root.mainloop()

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

        # Check for duplicate conduit names
        for block in canvas.data["blocks"]:
            if block.conduit and block.name == name:
                messagebox.showerror("Duplicate Error", f"Conduit '{name}' already exists.")
                return

        # Determine type based on width
        if width.isdigit():
            width = int(width)
            if width <= 1:
                final_type = "std_logic" if base_type.lower() in ["std_logic_vector", "signed", "unsigned"] else base_type
            else:
                if base_type.lower() in ["signed", "unsigned", "std_logic_vector"]:
                    final_type = f"{base_type}({width-1}:0)"
                else:
                    final_type = base_type
        else:
            final_type = base_type

        conduit = EntityBlock(canvas, 100, 100, name, [{"name": name, "dir": direction, "type": final_type}], conduit=True)
        canvas.data["blocks"].append(conduit)
        conduit_window.destroy()

    tk.Button(conduit_window, text="Create", command=create_conduit).pack(pady=10)
