#port_symbol.py
import tkinter as tk
from utils import check_dir, types_compatible, extract_kind, extract_width
from color_manager import ColorManager

class PortSymbol:
    cm = ColorManager()
    def __init__(self, canvas, x, y, block, port, inside, inherited_color=None):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.block = block
        self.port = port
        self.is_conduit = False

        k = port["type"].lower()
        self.shape = "square"
        self.r = 5
        if "std_logic" in k and "vector" not in k:
            self.shape = "circle"

        if self.shape == "circle":
            self.id = self.canvas.create_oval(self.x - self.r, self.y - self.r,
                                              self.x + self.r, self.y + self.r,
                                              fill="black", outline="black")
        else:
            s = 10
            self.r = s / 2
            self.id = self.canvas.create_rectangle(self.x - self.r, self.y - self.r,
                                                   self.x + self.r, self.y + self.r,
                                                   fill="black", outline="black")

        disp_label = port["name"]
        if port["dir"] in ["in", "inout"]:
            off = 15
            anch = "w"
        else:
            off = -15
            anch = "e"
        self.label_id = self.canvas.create_text(self.x + off, self.y, text=disp_label, anchor=anch, fill="black")

        self.canvas.tag_bind(self.id,       "<ButtonPress-1>",  self.on_press)
        self.canvas.tag_bind(self.id,       "<B1-Motion>",       self.on_drag)
        self.canvas.tag_bind(self.id,       "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.label_id, "<ButtonPress-1>",  self.on_press)
        self.canvas.tag_bind(self.label_id, "<B1-Motion>",       self.on_drag)
        self.canvas.tag_bind(self.label_id, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.id,       "<Button-3>",        self.on_port_right_click)
        self.canvas.tag_bind(self.label_id, "<Button-3>",        self.on_port_right_click)

        self.dragging = False
        self.color = inherited_color if inherited_color else None
        if not self.color and port["dir"] in ["out", "inout"]:
            self.color = PortSymbol.cm.get_next_color()

    def on_press(self, event):
        self.dragging = True
        if self.canvas.data["active_line"] is None:
            ln = self.canvas.create_line(
                self.x, self.y, self.x, self.y,
                fill=self.color if self.color else "black",
                tags=("wire",),
                smooth=True, splinesteps=36, width=3
            )
            self.canvas.data["active_line"] = ln
            self.canvas.data["active_port"] = self

    def on_drag(self, event):
        if self.dragging and self.canvas.data["active_line"]:
            stx, sty = self.x, self.y
            ex = self.canvas.canvasx(event.x)
            ey = self.canvas.canvasy(event.y)
            cx1 = stx + (ex - stx) / 2
            cy1 = sty
            cx2 = stx + (ex - stx) / 2
            cy2 = ey
            self.canvas.coords(
                self.canvas.data["active_line"],
                stx, sty, cx1, cy1, cx2, cy2, ex, ey
            )

    def on_release(self, event):
        if not self.dragging:
            return
        self.dragging = False

        line_id = self.canvas.data["active_line"]
        source_port = self.canvas.data["active_port"]
        success = False

        ex = self.canvas.canvasx(event.x)
        ey = self.canvas.canvasy(event.y)

        # Increase the overlapping area to ensure port is detected after panning
        overlapping = self.canvas.find_overlapping(ex-5, ey-5, ex+5, ey+5)
        for obj_id in overlapping:
            if obj_id != self.id and obj_id in self.canvas.data["port_map"]:
                target_port = self.canvas.data["port_map"][obj_id]
                if target_port != source_port and check_dir(source_port.port["dir"], target_port.port["dir"]):
                    a_kind  = extract_kind(source_port.port["type"])
                    a_width = extract_width(source_port.port["type"])
                    b_kind  = extract_kind(target_port.port["type"])
                    b_width = extract_width(target_port.port["type"])
                    if types_compatible({"kind":a_kind,"width":a_width},
                                        {"kind":b_kind,"width":b_width}):
                        self.update_wire(line_id, source_port, target_port)
                        success = True
                    else:
                        mx = (source_port.x + target_port.x) / 2
                        my = (source_port.y + target_port.y) / 2
                        self.prompt_adapter(mx, my, source_port.port, target_port.port, source_port, target_port, line_id)
                        success = True

        if not success:
            self.canvas.delete(line_id)
        self.canvas.data["active_line"] = None
        self.canvas.data["active_port"] = None

    def update_wire(self, ln, sp, tp):
        self.canvas.coords(
            ln,
            sp.x, sp.y,
            (sp.x + tp.x) / 2, sp.y,
            (sp.x + tp.x) / 2, tp.y,
            tp.x, tp.y
        )
        self.canvas.itemconfig(ln, smooth=True, splinesteps=36, width=3,
                               fill=self.color if self.color else "black")
        self.canvas.data["connections"].append((sp, tp, ln, None))

    def prompt_adapter(self, mx, my, a_info, b_info, sp, tp, ln):
        def do_create(mode_str):
            w.destroy()
            cb = self.canvas.data.get("create_adapter_cb", None)
            if cb:
                cb(mx, my, a_info, b_info, sp, tp, ln, sp.color)

        w = tk.Toplevel(self.canvas)
        w.title("Mismatch")
        tk.Label(w, text="Insert Adapter?").pack()
        mode_var = tk.StringVar(w, "Convert")
        tk.Radiobutton(w, text="Convert",          variable=mode_var, value="Convert").pack()
        tk.Radiobutton(w, text="TruncateOrExtend", variable=mode_var, value="TruncateOrExtend").pack()
        tk.Button(w, text="OK", command=lambda: do_create(mode_var.get())).pack()

    def on_port_right_click(self, event):
        menu = tk.Menu(self.canvas, tearoff=0)
        if not self.is_conduit:
            menu.add_command(label="Export as Conduit", command=self.export_as_conduit)
        else:
            menu.add_command(label="Remove Conduit", command=self.remove_conduit)
        menu.add_separator()
        menu.add_command(label="Remove All Connections", command=self.remove_all_connections)
        menu.post(event.x_root, event.y_root)

    def export_as_conduit(self):
        if not self.is_conduit:
            self.is_conduit = True
            self.canvas.itemconfig(self.id, outline="red")

    def remove_conduit(self):
        if self.is_conduit:
            self.is_conduit = False
            self.canvas.itemconfig(self.id, outline="black")

    def remove_all_connections(self):
        conns = [c for c in self.canvas.data["connections"] if c[0] == self or c[1] == self]
        for c_ in conns:
            self.canvas.delete(c_[2])
            self.canvas.data["connections"].remove(c_)
