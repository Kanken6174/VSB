# gui_components.py
import tkinter as tk
from tkinter import messagebox
from parser import extract_kind, extract_width, check_dir, types_compatible

DEBUG = True

class PortSymbol:
    def __init__(self, canvas, x, y, block, port):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.block = block
        self.port = port
        self.meta = {
            "kind": extract_kind(port["type"]),
            "width": extract_width(port["type"]),
            "type": port["type"]
        }
        if DEBUG:
            print(f"Creating port symbol: {port['name']} | Type: {port['type']} | Kind: {self.meta['kind']} | Width: {self.meta['width']}")
    
        width = self.meta["width"]
        use_square = True
        if self.meta["kind"] == "SL" and width == 1:
            use_square = False
        self.shape = "square" if use_square else "circle"
    
        if self.shape == "circle":
            self.r = 5
            self.id = self.canvas.create_oval(
                self.x - self.r, self.y - self.r,
                self.x + self.r, self.y + self.r,
                fill="black"
            )
        else:
            s = 10
            self.r = s / 2
            self.id = self.canvas.create_rectangle(
                self.x - self.r, self.y - self.r,
                self.x + self.r, self.y + self.r,
                fill="black"
            )
    
        display = port["name"]
        if width and width > 1:
            display += f"[{width-1}:0]"
    
        offset = -10 if port["dir"] in ["in", "inout"] else 10
        anchor = "e" if offset < 0 else "w"
        self.label_id = self.canvas.create_text(
            self.x + offset, self.y,
            text=display,
            anchor=anchor
        )
    
        self.canvas.tag_bind(self.id, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.id, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.label_id, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.label_id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.label_id, "<ButtonRelease-1>", self.on_release)
        
        self.canvas.tag_bind(self.id, "<Button-3>", self.on_port_right_click)
        self.canvas.tag_bind(self.label_id, "<Button-3>", self.on_port_right_click)
        
        self.dragging = False
        self.is_conduit = False
    
    def on_press(self, event):
        self.dragging = True
        if self.canvas.data["active_line"] is None:
            line = self.canvas.create_line(
                self.x, self.y, self.x, self.y, fill="black", tags=("wire",)
            )
            self.canvas.data["active_line"] = line
            self.canvas.data["active_port"] = self
    
    def on_drag(self, event):
        if self.dragging and self.canvas.data["active_line"] is not None:
            self.canvas.coords(
                self.canvas.data["active_line"],
                self.x, self.y, event.x, event.y
            )
    
    def on_release(self, event):
        if not self.dragging:
            return
        self.dragging = False
        line = self.canvas.data["active_line"]
        source_port = self.canvas.data["active_port"]
        target_port = None
        done = False
    
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for obj_id in overlapping:
            if obj_id != self.id and obj_id in self.canvas.data["port_map"]:
                cp = self.canvas.data["port_map"][obj_id]
                if cp != source_port and check_dir(source_port.port["dir"], cp.port["dir"]):
                    a = source_port.meta
                    b = cp.meta
                    if types_compatible(a, b):
                        self.canvas.coords(line, source_port.x, source_port.y, cp.x, cp.y)
                        self.canvas.data["connections"].append((source_port, cp, line, None))
                        done = True
                        break
                    else:
                        mx = (source_port.x + cp.x) / 2
                        my = (source_port.y + cp.y) / 2
                        self.prompt_adapter(mx, my, a, b, source_port, cp, line)
                        done = True
                        break
    
        if not done:
            self.canvas.delete(line)
    
        self.canvas.data["active_line"] = None
        self.canvas.data["active_port"] = None
    
    def prompt_adapter(self, mx, my, a, b, source_port, cp, line):
        def pick_adapter(mode):
            self.canvas.data["adapter_win"] = None
            adapter_window.destroy()
            self.canvas.delete(line)
            adapter = AdapterBlock(self.canvas, mx, my, a, b, mode)
            self.canvas.data["blocks"].append(adapter)
            line1 = self.canvas.create_line(source_port.x, source_port.y, adapter.left_port.x, adapter.left_port.y, fill="black", tags=("wire",))
            self.canvas.tag_bind("wire", "<Button-3>", self.on_wire_right_click)
            self.canvas.data["connections"].append((source_port, adapter.left_port, line1, adapter))
            line2 = self.canvas.create_line(adapter.right_port.x, adapter.right_port.y, cp.x, cp.y, fill="black", tags=("wire",))
            self.canvas.tag_bind("wire", "<Button-3>", self.on_wire_right_click)
            self.canvas.data["connections"].append((adapter.right_port, cp, line2, adapter))
    
        adapter_window = tk.Toplevel(self.canvas)
        adapter_window.title("Type/Width Mismatch")
        tk.Label(adapter_window, text="Type/Width mismatch. Insert Adapter?").pack(pady=5)
    
        mode_var = tk.StringVar(adapter_window, "Convert")
        tk.Radiobutton(adapter_window, text="Convert", variable=mode_var, value="Convert").pack(anchor="w")
        tk.Radiobutton(adapter_window, text="TruncateOrExtend", variable=mode_var, value="TruncateOrExtend").pack(anchor="w")
        tk.Button(adapter_window, text="OK", command=lambda: pick_adapter(mode_var.get())).pack(pady=5)
    
    def on_wire_right_click(self, event):
        wire = self.canvas.find_closest(event.x, event.y)[0]
        if "wire" in self.canvas.gettags(wire):
            menu = tk.Menu(self.canvas, tearoff=0)
            menu.add_command(label="Disconnect", command=lambda: self.disconnect_wire(wire))
            menu.post(event.x_root, event.y_root)
    
    def disconnect_wire(self, wire_id):
        self.canvas.delete(wire_id)
        connections_to_remove = [conn for conn in self.canvas.data["connections"] if conn[2] == wire_id]
        for conn in connections_to_remove:
            self.canvas.data["connections"].remove(conn)
    
    def on_port_right_click(self, event):
        menu = tk.Menu(self.canvas, tearoff=0)
        if not self.is_conduit:
            menu.add_command(label="Export as Conduit", command=lambda: self.export_as_conduit())
        else:
            menu.add_command(label="Remove Conduit", command=lambda: self.remove_conduit())
        menu.post(event.x_root, event.y_root)
    
    def export_as_conduit(self):
        if self.is_conduit:
            return
        self.canvas.itemconfig(self.id, fill="red")
        self.canvas.itemconfig(self.label_id, fill="red")
        self.is_conduit = True
        if DEBUG:
            print(f"Port '{self.port['name']}' on block '{self.block.name}' exported as conduit.")
    
    def remove_conduit(self):
        if not self.is_conduit:
            return
        self.canvas.itemconfig(self.id, fill="black")
        self.canvas.itemconfig(self.label_id, fill="black")
        self.is_conduit = False
        if DEBUG:
            print(f"Port '{self.port['name']}' on block '{self.block.name}' conduit removed.")

class AdapterBlock:
    def __init__(self, canvas, x, y, metaA, metaB, mode):
        self.canvas = canvas
        self.name = "Adapter"
        self.x = x
        self.y = y
        self.mode = mode
        self.dragging = False
        self.ox = 0
        self.oy = 0
        size = 25
        self.obj = self.canvas.create_polygon(
            self.x, self.y - size,
            self.x - size, self.y,
            self.x, self.y + size,
            self.x + size, self.y,
            fill="pink"
        )
        self.text = self.canvas.create_text(self.x, self.y, text="Adapter", font=("Arial", 10))

        self.canvas.tag_bind(self.obj, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.text, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.obj, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.text, "<Button-3>", self.on_right_click)

        self.menu = tk.Menu(self.canvas, tearoff=0)
        self.menu.add_command(label="Delete", command=self.delete_self)
        self.menu.add_command(label="Rename", command=self.rename_self)
        self.menu.add_command(label="Edit Adapter", command=self.edit_adapter)

        ist = self.construct_type(metaA)
        ost = self.construct_type(metaB)

        self.left_port = PortSymbol(self.canvas, self.x - 30, self.y, self, {"name": "Din", "dir": "in", "type": ist})
        self.right_port = PortSymbol(self.canvas, self.x + 30, self.y, self, {"name": "Dout", "dir": "out", "type": ost})

        self.canvas.data["port_map"][self.left_port.id] = self.left_port
        self.canvas.data["port_map"][self.left_port.label_id] = self.left_port
        self.canvas.data["port_map"][self.right_port.id] = self.right_port
        self.canvas.data["port_map"][self.right_port.label_id] = self.right_port

    def construct_type(self, meta):
        kind = meta["kind"]
        width = meta["width"]
        if kind in ["SLV", "SIGNED", "UNSIGNED"] and width:
            if kind == "SLV":
                return f"std_logic_vector({width-1}:0)" if width > 1 else "std_logic"
            else:
                return f"{kind.lower()}({width-1}:0)" if width > 1 else f"{kind.lower()}(0:0)"
        elif kind == "INTEGER":
            return "integer"
        return "std_logic"

    def on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def delete_self(self):
        for port in [self.left_port, self.right_port]:
            self.remove_port(port)
        self.canvas.delete(self.obj)
        self.canvas.delete(self.text)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def remove_port(self, port):
        for connection in self.canvas.data["connections"][:]:
            if connection[0] == port or connection[1] == port:
                self.canvas.delete(connection[2])
                self.canvas.data["connections"].remove(connection)
        self.canvas.delete(port.id)
        self.canvas.delete(port.label_id)
        if port.id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.id]
        if port.label_id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.label_id]

    def rename_self(self):
        rename_window = tk.Toplevel(self.canvas)
        rename_window.title("Rename Adapter")
        tk.Label(rename_window, text="New Name:").pack(pady=5)
        name_entry = tk.Entry(rename_window)
        name_entry.insert(0, self.name)
        name_entry.pack(pady=5)

        def apply_rename():
            new_name = name_entry.get().strip()
            if new_name:
                self.name = new_name
                self.canvas.itemconfig(self.text, text=new_name)
                rename_window.destroy()

        tk.Button(rename_window, text="OK", command=apply_rename).pack(pady=5)

    def edit_adapter(self):
        edit_window = tk.Toplevel(self.canvas)
        edit_window.title("Edit Adapter Properties")
        tk.Label(edit_window, text="Adapter Mode:").pack(pady=5)
        mode_entry = tk.Entry(edit_window)
        mode_entry.insert(0, self.mode)
        mode_entry.pack(pady=5)

        def apply_edit():
            self.mode = mode_entry.get().strip()
            edit_window.destroy()

        tk.Button(edit_window, text="OK", command=apply_edit).pack(pady=5)

    def on_click(self, event):
        if not self.dragging:
            self.dragging = True
            coords = self.canvas.coords(self.obj)
            cx = (coords[0] + coords[4]) / 2
            cy = (coords[1] + coords[5]) / 2
            self.ox = cx - event.x
            self.oy = cy - event.y
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_drag(self, event):
        if not self.dragging:
            return
        new_x = event.x + self.ox
        new_y = event.y + self.oy
        dx = new_x - self.x
        dy = new_y - self.y
        self.x = new_x
        self.y = new_y
        self.canvas.move(self.obj, dx, dy)
        self.canvas.move(self.text, dx, dy)
        for port in [self.left_port, self.right_port]:
            port.x += dx
            port.y += dy
            self.canvas.move(port.id, dx, dy)
            self.canvas.move(port.label_id, dx, dy)
            for connection in self.canvas.data["connections"]:
                if connection[0] == port or connection[1] == port:
                    self.canvas.coords(connection[2],
                                       connection[0].x, connection[0].y,
                                       connection[1].x, connection[1].y)

    def on_release(self, event):
        self.dragging = False
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

class EntityBlock:
    def __init__(self, canvas, x, y, name, generics, ports, conduit=False):
        self.canvas = canvas
        self.name = name
        self.generics = generics
        self.ports = ports
        self.conduit = conduit
        self.dragging = False
        self.ox = 0
        self.oy = 0

        lines = [name] + [f"{p['dir']} {p['name']}" for p in ports]
        max_length = max(len(s) for s in lines) if lines else 10
        self.width = 10 * max_length
        self.height = max(40 + len(ports) * 20, 60)
        fill_color = "lightyellow" if conduit else "lightblue"
        self.obj = self.canvas.create_rectangle(
            x, y, x + self.width, y + self.height,
            fill=fill_color
        )
        self.title_id = self.canvas.create_text(
            x + 5, y + 5,
            anchor="nw",
            text=name,
            font=("Arial", 10)
        )
        self.x = x
        self.y = y

        self.canvas.tag_bind(self.obj, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.title_id, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.obj, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.title_id, "<Button-1>", self.on_click)

        self.menu = tk.Menu(self.canvas, tearoff=0)
        self.menu.add_command(label="Delete", command=self.delete_self)
        if conduit:
            self.menu.add_command(label="Rename", command=self.rename_self)
        if generics:
            self.menu.add_command(label="Edit Generics", command=self.edit_generics)

        self.port_symbols = []
        left_count = 0
        right_count = 0
        port_start_y = y + 40
        for port in ports:
            if conduit:
                if port["dir"] == "in":
                    flipped_dir = "out"
                elif port["dir"] == "out":
                    flipped_dir = "in"
                else:
                    flipped_dir = "inout"
                port_flipped = {"name": port["name"], "dir": flipped_dir, "type": port["type"]}
                
                if flipped_dir in ["out", "inout"]:
                    px = x + self.width
                    py = port_start_y + right_count * 20
                    right_count += 1
                else:
                    px = x
                    py = port_start_y + left_count * 20
                    left_count += 1
                ps = PortSymbol(self.canvas, px, py, self, port_flipped)
            else:
                if port["dir"] in ["in", "inout"]:
                    px = x
                    py = port_start_y + left_count * 20
                    left_count += 1
                else:
                    px = x + self.width
                    py = port_start_y + right_count * 20
                    right_count += 1
                ps = PortSymbol(self.canvas, px, py, self, port)
            self.canvas.data["port_map"][ps.id] = ps
            self.canvas.data["port_map"][ps.label_id] = ps
            self.port_symbols.append(ps)

        self.generic_values = {}
        if self.generics:
            self.prompt_generics()

    def prompt_generics(self):
        generic_window = tk.Toplevel(self.canvas)
        generic_window.title(f"Set Generics for {self.name}")
        self.generic_entries = {}

        for generic in self.generics:
            frame = tk.Frame(generic_window)
            frame.pack(pady=2, padx=5, fill='x')

            tk.Label(frame, text=f"{generic['name']} ({generic['type']}):").pack(side="left")
            entry = tk.Entry(frame)
            entry.pack(side="left", fill="x", expand=True)
            if generic.get("default"):
                entry.insert(0, generic["default"])
            self.generic_entries[generic['name']] = entry

        def apply_generics():
            try:
                for gen in self.generics:
                    name = gen['name']
                    value = self.generic_entries[name].get().strip()
                    if not value:
                        value = gen.get("default")
                    if gen['type'].lower() == 'integer':
                        value = int(value)
                    elif gen['type'].lower() == 'string':
                        if not (value.startswith('"') and value.endswith('"')):
                            value = f'"{value}"'
                    self.generic_values[name] = value
                generic_window.destroy()
            except ValueError as ve:
                messagebox.showerror("Input Error", f"Invalid value for generic '{name}'. Expected type {gen['type']}.")

        tk.Button(generic_window, text="OK", command=apply_generics).pack(pady=5)

    def edit_generics(self):
        edit_window = tk.Toplevel(self.canvas)
        edit_window.title(f"Edit Generics for {self.name}")
        self.generic_entries = {}

        for generic in self.generics:
            frame = tk.Frame(edit_window)
            frame.pack(pady=2, padx=5, fill='x')

            current_value = self.generic_values.get(generic['name'], generic.get("default", ""))
            tk.Label(frame, text=f"{generic['name']} ({generic['type']}):").pack(side="left")
            entry = tk.Entry(frame)
            entry.pack(side="left", fill="x", expand=True)
            entry.insert(0, current_value)
            self.generic_entries[generic['name']] = entry

        def apply_edit_generics():
            try:
                for gen in self.generics:
                    name = gen['name']
                    value = self.generic_entries[name].get().strip()
                    if not value:
                        value = gen.get("default")
                    if gen['type'].lower() == 'integer':
                        value = int(value)
                    elif gen['type'].lower() == 'string':
                        if not (value.startswith('"') and value.endswith('"')):
                            value = f'"{value}"'
                    self.generic_values[name] = value
                edit_window.destroy()
            except ValueError as ve:
                messagebox.showerror("Input Error", f"Invalid value for generic '{name}'. Expected type {gen['type']}.")

        tk.Button(edit_window, text="OK", command=apply_edit_generics).pack(pady=5)

    def on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def delete_self(self):
        for port in self.port_symbols:
            self.remove_port(port)
        self.canvas.delete(self.obj)
        self.canvas.delete(self.title_id)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def remove_port(self, port):
        for connection in self.canvas.data["connections"][:]:
            if connection[0] == port or connection[1] == port:
                self.canvas.delete(connection[2])
                self.canvas.data["connections"].remove(connection)
        self.canvas.delete(port.id)
        self.canvas.delete(port.label_id)
        if port.id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.id]
        if port.label_id in self.canvas.data["port_map"]:
            del self.canvas.data["port_map"][port.label_id]

    def rename_self(self):
        rename_window = tk.Toplevel(self.canvas)
        rename_window.title("Rename Entity")
        tk.Label(rename_window, text="New Name:").pack(pady=5)
        name_entry = tk.Entry(rename_window)
        name_entry.insert(0, self.name)
        name_entry.pack(pady=5)

        def apply_rename():
            new_name = name_entry.get().strip()
            if new_name:
                self.name = new_name
                self.canvas.itemconfig(self.title_id, text=new_name)
                rename_window.destroy()

        tk.Button(rename_window, text="OK", command=apply_rename).pack(pady=5)

    def on_click(self, event):
        if not self.dragging:
            self.dragging = True
            self.ox = self.x - event.x
            self.oy = self.y - event.y
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_drag(self, event):
        if not self.dragging:
            return
        new_x = event.x + self.ox
        new_y = event.y + self.oy
        dx = new_x - self.x
        dy = new_y - self.y
        self.x = new_x
        self.y = new_y
        self.canvas.move(self.obj, dx, dy)
        self.canvas.move(self.title_id, dx, dy)

        for port in self.port_symbols:
            port.x += dx
            port.y += dy
            self.canvas.move(port.id, dx, dy)
            self.canvas.move(port.label_id, dx, dy)
            for connection in self.canvas.data["connections"]:
                if connection[0] == port or connection[1] == port:
                    self.canvas.coords(connection[2],
                                       connection[0].x, connection[0].y,
                                       connection[1].x, connection[1].y)

    def on_release(self, event):
        self.dragging = False
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
