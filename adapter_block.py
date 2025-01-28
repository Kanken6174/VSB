#adapter_block.py
import tkinter as tk
from base_block import DraggableBlock
from port_symbol import PortSymbol

class AdapterBlock(DraggableBlock):
    def __init__(self, canvas, x, y, metaA, metaB, mode, inherited_color=None):
        super().__init__(canvas, x, y)
        self.name = "Adapter"
        self.mode = mode
        self.obj = self.canvas.create_polygon(
            self.x,   self.y-25,
            self.x-25,self.y,
            self.x,   self.y+25,
            self.x+25,self.y,
            fill="pink", outline="black"
        )
        self.text = self.canvas.create_text(self.x, self.y, text="Adapter", font=("Arial",10))
        self.canvas.tag_bind(self.obj, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.text, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.obj, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.text, "<Button-3>", self.on_right_click)
        self.menu = tk.Menu(self.canvas, tearoff=0)
        self.menu.add_command(label="Delete", command=self.delete_self)
        self.menu.add_command(label="Rename", command=self.rename_self)
        self.menu.add_command(label="Edit Adapter", command=self.edit_adapter)
        self.menu.add_separator()
        self.menu.add_command(label="Remove All Connections", command=self.remove_all_connections)

        itA = self.construct_type(metaA)
        itB = self.construct_type(metaB)
        self.left_port = PortSymbol(self.canvas, self.x-30, self.y, self, {"name":"Din","dir":"in","type":itA}, True, inherited_color)
        self.right_port= PortSymbol(self.canvas, self.x+30, self.y, self, {"name":"Dout","dir":"out","type":itB}, True)
        if self.left_port.color:
            self.right_port.color=self.left_port.color

        pm = self.canvas.data["port_map"]
        pm[self.left_port.id] = self.left_port
        pm[self.left_port.label_id] = self.left_port
        pm[self.right_port.id] = self.right_port
        pm[self.right_port.label_id] = self.right_port

    def construct_type(self, m):
        k = m["kind"]
        w = m["width"]
        if k in ["SLV","SIGNED","UNSIGNED"] and w:
            if k=="SLV":
                return f"std_logic_vector({w-1}:0)" if w>1 else "std_logic"
            else:
                return f"{k.lower()}({w-1}:0)" if w>1 else f"{k.lower()}(0:0)"
        if k == "INTEGER":
            return "integer"
        return "std_logic"

    def on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def delete_self(self):
        self.remove_port(self.left_port)
        self.remove_port(self.right_port)
        self.canvas.delete(self.obj)
        self.canvas.delete(self.text)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def rename_self(self):
        self.rename_block("Rename Adapter")

    def edit_adapter(self):
        w = tk.Toplevel(self.canvas)
        w.title("Edit Adapter")
        tk.Label(w, text="Adapter Mode:").pack()
        e = tk.Entry(w)
        e.insert(0, self.mode)
        e.pack()
        def ok():
            self.mode = e.get().strip()
            w.destroy()
        tk.Button(w, text="OK", command=ok).pack()

    def remove_all_connections(self):
        cs = []
        for p in [self.left_port, self.right_port]:
            cs.extend([c for c in self.canvas.data["connections"] if c[0] == p or c[1] == p])
        for c_ in cs:
            self.canvas.delete(c_[2])
            self.canvas.data["connections"].remove(c_)

    def move_block(self, dx, dy):
        self.canvas.move(self.obj, dx, dy)
        self.canvas.move(self.text, dx, dy)

    def move_ports(self, dx, dy):
        self.left_port.x += dx
        self.left_port.y += dy
        self.right_port.x+= dx
        self.right_port.y+= dy
        self.canvas.move(self.left_port.id, dx, dy)
        self.canvas.move(self.left_port.label_id, dx, dy)
        self.canvas.move(self.right_port.id, dx, dy)
        self.canvas.move(self.right_port.label_id, dx, dy)

    def update_connections(self):
        cd = self.canvas.data["connections"]
        for c in cd:
            if c[0] == self.left_port or c[1] == self.left_port:
                self.update_curved_line(c[2], c[0], c[1])
            if c[0] == self.right_port or c[1] == self.right_port:
                self.update_curved_line(c[2], c[0], c[1])
