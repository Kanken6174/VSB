#entity_block.py
import tkinter as tk
from base_block import DraggableBlock
from port_symbol import PortSymbol

class EntityBlock(DraggableBlock):
    def __init__(self, canvas, x, y, name, generics, ports, conduit=False):
        super().__init__(canvas, x, y)
        self.name = name
        self.generics = generics
        self.ports = ports
        self.conduit = conduit
        lines = [name] + [p["dir"]+" "+p["name"] for p in ports]
        ml = 10
        if lines:
            ml = max(len(s) for s in lines)
        self.width = max(100, 12*ml)
        ic = sum(1 for p in ports if p["dir"]=="in")
        oc = sum(1 for p in ports if p["dir"]=="out")
        mp = max(ic,oc)
        self.height = max(40+mp*20, 60)
        fc = "lightyellow" if conduit else "lightblue"
        self.obj = self.canvas.create_rectangle(
            x, y, x+self.width, y+self.height, fill=fc, outline="black"
        )
        self.text = self.canvas.create_text(
            x+self.width/2, y+10, text=name, font=("Arial",10), anchor="n", fill="black"
        )
        self.canvas.tag_bind(self.obj, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.text, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.obj, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.text, "<Button-1>", self.on_click)
        self.menu = tk.Menu(self.canvas, tearoff=0)
        self.menu.add_command(label="Delete", command=self.delete_self)
        if not conduit:
            self.menu.add_command(label="Rename", command=self.rename_self)
        if generics:
            self.menu.add_command(label="Edit Generics", command=self.edit_generics)
        self.menu.add_separator()
        self.menu.add_command(label="Remove All Connections", command=self.remove_all_connections)
        self.port_symbols = []
        lc = 0
        rc = 0
        sy = y + 30
        for p in ports:
            if conduit:
                if p["dir"] == "in":
                    fd = "in"
                elif p["dir"] == "out":
                    fd = "out"
                else:
                    fd = "inout"
                pf = {"name":p["name"], "dir":fd, "type":p["type"]}
                if fd in ["out","inout"]:
                    px = x + self.width - 30
                    py = sy + rc*20
                    rc += 1
                else:
                    px = x + 30
                    py = sy + lc*20
                    lc += 1
                ps = PortSymbol(self.canvas, px, py, self, pf, True)
            else:
                if p["dir"] in ["in","inout"]:
                    px = x - 10
                    py = sy + lc*20
                    lc += 1
                else:
                    px = x + self.width + 10
                    py = sy + rc*20
                    rc += 1
                ps = PortSymbol(self.canvas, px, py, self, p, False)

            self.canvas.data["port_map"][ps.id] = ps
            self.canvas.data["port_map"][ps.label_id] = ps
            self.port_symbols.append(ps)

        self.generic_values = {}
        if self.generics:
            self.prompt_generics()

    def on_right_click(self, event):
        self.menu.post(event.x_root, event.y_root)

    def delete_self(self):
        for p in self.port_symbols[:]:
            self.remove_port(p)
        self.canvas.delete(self.obj)
        self.canvas.delete(self.text)
        if self in self.canvas.data["blocks"]:
            self.canvas.data["blocks"].remove(self)

    def rename_self(self):
        self.rename_block("Rename Entity")

    def move_block(self, dx, dy):
        self.canvas.move(self.obj, dx, dy)
        self.canvas.move(self.text, dx, dy)

    def move_ports(self, dx, dy):
        for p in self.port_symbols:
            p.x += dx
            p.y += dy
            self.canvas.move(p.id, dx, dy)
            self.canvas.move(p.label_id, dx, dy)

    def update_connections(self):
        cd = self.canvas.data["connections"]
        for c in cd:
            if c[0] in self.port_symbols or c[1] in self.port_symbols:
                self.update_curved_line(c[2], c[0], c[1])

    def remove_all_connections(self):
        cs = []
        for p in self.port_symbols:
            cs.extend([c for c in self.canvas.data["connections"] if c[0] == p or c[1] == p])
        for c_ in cs:
            self.canvas.delete(c_[2])
            self.canvas.data["connections"].remove(c_)

    def prompt_generics(self):
        w = tk.Toplevel(self.canvas)
        w.title("Set Generics for "+self.name)
        self.generic_entries = {}
        for g in self.generics:
            f = tk.Frame(w)
            f.pack(pady=2,padx=5,fill='x')
            tk.Label(f, text=g["name"] + " ("+g["type"]+"):").pack(side="left")
            e = tk.Entry(f)
            e.pack(side="left", fill="x", expand=True)
            if g.get("default"):
                e.insert(0, g["default"])
            self.generic_entries[g["name"]] = e
        def ok():
            for g in self.generics:
                n = g["name"]
                v = self.generic_entries[n].get().strip()
                if not v:
                    v = g.get("default")
                if g["type"].lower() == "integer":
                    v = int(v)
                elif g["type"].lower() == "string":
                    if not (v.startswith('"') and v.endswith('"')):
                        v = '"'+v+'"'
                self.generic_values[n] = v
            w.destroy()
        tk.Button(w, text="OK", command=ok).pack(pady=5)

    def edit_generics(self):
        w = tk.Toplevel(self.canvas)
        w.title("Edit Generics for "+self.name)
        self.generic_entries = {}
        for g in self.generics:
            f = tk.Frame(w)
            f.pack(pady=2,padx=5,fill='x')
            cv = self.generic_values.get(g["name"], g.get("default",""))
            tk.Label(f, text=g["name"]+" ("+g["type"]+"):").pack(side="left")
            e = tk.Entry(f)
            e.pack(side="left", fill="x", expand=True)
            e.insert(0, str(cv))
            self.generic_entries[g["name"]] = e
        def ok():
            for g in self.generics:
                n = g["name"]
                v = self.generic_entries[n].get().strip()
                if not v:
                    v = g.get("default")
                if g["type"].lower() == "integer":
                    v = int(v)
                elif g["type"].lower() == "string":
                    if not (v.startswith('"') and v.endswith('"')):
                        v = '"'+v+'"'
                self.generic_values[n] = v
            w.destroy()
        tk.Button(w, text="OK", command=ok).pack(pady=5)
