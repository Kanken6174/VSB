import tkinter as tk
import os
import json
from parser import find_blocks
from entity_block import EntityBlock
from adapter_block import AdapterBlock
from generator import generate_top_level

def create_adapter(canvas, mx, my, atypeA, atypeB, source_port, target_port, old_line, inherited_color):
    if old_line:
        canvas.delete(old_line)
    adapter = AdapterBlock(canvas, mx, my, atypeA, atypeB, "Convert", inherited_color)
    canvas.data["blocks"].append(adapter)
    adapter.left_port.port["type"] = atypeA["type"]
    adapter.right_port.port["type"] = atypeB["type"]
    line1 = canvas.create_line(source_port.x, source_port.y, adapter.left_port.x, adapter.left_port.y,
        fill = source_port.color if source_port.color else "black", tags=("wire",),
        smooth=True, splinesteps=36, width=3)
    canvas.data["connections"].append((source_port, adapter.left_port, line1, adapter))
    line2 = canvas.create_line(adapter.right_port.x, adapter.right_port.y, target_port.x, target_port.y,
        fill = source_port.color if source_port.color else "black", tags=("wire",),
        smooth=True, splinesteps=36, width=3)
    canvas.data["connections"].append((adapter.right_port, target_port, line2, adapter))
    canvas.tag_bind("wire", "<Button-3>", lambda e: wire_right_click(e, canvas))

def wire_right_click(e, canvas):
    w = canvas.find_closest(e.x, e.y)[0]
    if "wire" in canvas.gettags(w):
        m = tk.Menu(canvas, tearoff=0)
        m.add_command(label="Disconnect", command=lambda: disconnect_wire(canvas, w))
        m.post(e.x_root, e.y_root)

def disconnect_wire(canvas, w):
    canvas.delete(w)
    cs = canvas.data["connections"]
    r = [x for x in cs if x[2] == w]
    for x in r:
        cs.remove(x)

def load_previous_configuration(canvas, path):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        data = json.load(f)
    bdata = data.get("blocks", [])
    cdata = data.get("connections", [])
    nb = []
    for bd in bdata:
        t = bd["type"]
        n = bd["name"]
        x = bd["x"]
        y = bd["y"]
        if t == "adapter":
            a = AdapterBlock(canvas, x, y, {"kind":"SLV","width":1}, {"kind":"SLV","width":1}, "Convert")
            a.name = n
            canvas.itemconfig(a.text, text=n)
            a.x = x
            a.y = y
            co = canvas.coords(a.obj)
            cx = (co[0] + co[4]) / 2
            cy = (co[1] + co[5]) / 2
            dx = x - cx
            dy = y - cy
            canvas.move(a.obj, dx, dy)
            canvas.move(a.text, dx, dy)
            a.left_port.x = x - 30
            a.left_port.y = y
            a.right_port.x = x + 30
            a.right_port.y = y
            canvas.move(a.left_port.id, dx, dy)
            canvas.move(a.left_port.label_id, dx, dy)
            canvas.move(a.right_port.id, dx, dy)
            canvas.move(a.right_port.label_id, dx, dy)
            nb.append(a)
        else:
            g = bd.get("generics", [])
            ps = bd.get("ports", [])
            ep = []
            for p_ in ps:
                ep.append({
                    "name": p_["port_name"],
                    "dir":  p_["port_dir"],
                    "type": p_["port_type"]
                })
            e = EntityBlock(canvas, x, y, n, g, ep, bd.get("conduit",False))
            e.name = n
            e.x = x
            e.y = y
            if bd.get("generic_values"):
                e.generic_values = bd["generic_values"]
            co = canvas.coords(e.obj)
            dx = x - co[0]
            dy = y - co[1]
            canvas.move(e.obj, dx, dy)
            canvas.move(e.text, dx, dy)
            for i,pps in enumerate(e.port_symbols):
                px = ps[i]["x"]
                py = ps[i]["y"]
                pdx = px - pps.x
                pdy = py - pps.y
                pps.x = px
                pps.y = py
                canvas.move(pps.id, pdx, pdy)
                canvas.move(pps.label_id, pdx, pdy)
                pps.is_conduit = ps[i]["is_conduit"]
                if pps.is_conduit:
                    canvas.itemconfig(pps.id, outline="red")
            nb.append(e)
    canvas.data["blocks"].extend(nb)
    nm = {}
    for x in nb:
        nm[x.name] = x
    pm = {}
    for x in nb:
        for ps in x.port_symbols:
            pm[(x.name, ps.port["name"])] = ps
    for c_ in cdata:
        b1 = c_["block1"]
        b2 = c_["block2"]
        p1 = c_["port1"]
        p2 = c_["port2"]
        if (b1, p1) in pm and (b2, p2) in pm:
            pp1 = pm[(b1, p1)]
            pp2 = pm[(b2, p2)]
            cl = pp1.color if pp1.color else "black"
            ln = canvas.create_line(pp1.x, pp1.y, pp2.x, pp2.y, fill=cl, tags=("wire",),
                                    smooth=True, splinesteps=36, width=3)
            canvas.data["connections"].append((pp1, pp2, ln, None))
            cx1 = pp1.x + (pp2.x - pp1.x)/2
            cy1 = pp1.y
            cx2 = pp1.x + (pp2.x - pp1.x)/2
            cy2 = pp2.y
            canvas.coords(ln, pp1.x, pp1.y, cx1, cy1, cx2, cy2, pp2.x, pp2.y)
    for w in canvas.find_withtag("wire"):
        canvas.tag_bind(w, "<Button-3>", lambda e: wire_right_click(e, canvas))

def run_gui(directory):
    blocks = find_blocks(directory)
    root = tk.Tk()
    root.title("Efinix System Builder")
    left_frame = tk.Frame(root)
    left_frame.pack(side="left", fill="y", padx=5, pady=5)

    tk.Label(left_frame, text="Available Blocks").pack()
    blocks_listbox = tk.Listbox(left_frame)
    blocks_listbox.pack(fill="both", expand=True)
    for b in blocks:
        nm, gen, pts = b
        blocks_listbox.insert("end",
            ("Empty Block: " if not gen and not pts else "Entity/Component: ")
            + nm
        )

    def add_conduit(root_window, cvs):
        w = tk.Toplevel(root_window)
        w.title("New Conduit")
        tk.Label(w, text="Name:").pack()
        ne = tk.Entry(w)
        ne.insert(0, "sig")
        ne.pack()
        tk.Label(w, text="Direction:").pack()
        dv = tk.StringVar(w, "in")
        tk.OptionMenu(w, dv, "in", "out", "inout").pack()
        tk.Label(w, text="Bit width:").pack()
        we = tk.Entry(w)
        we.insert(0, "1")
        we.pack()
        tk.Label(w, text="Base Type:").pack()
        te = tk.Entry(w)
        te.insert(0, "std_logic")
        te.pack()
        def ok():
            nm = ne.get().strip()
            dr = dv.get()
            wd = we.get().strip()
            bt = te.get().strip()
            if not nm:
                tk.messagebox.showerror("Error", "Conduit name cannot be empty.")
                return
            for bb in cvs.data["blocks"]:
                if hasattr(bb, "conduit") and bb.conduit and bb.name == nm:
                    tk.messagebox.showerror("Error", "Conduit '" + nm + "' already exists.")
                    return
            final_type = bt
            if wd.isdigit():
                wd = int(wd)
                if wd <= 1:
                    if bt.lower() in ["std_logic_vector", "signed", "unsigned", "std_logic"]:
                        final_type = "std_logic"
                else:
                    if bt.lower() == "std_logic":
                        final_type = "std_logic_vector(" + str(wd - 1) + ":0)"
                    elif bt.lower() in ["signed", "unsigned", "std_logic_vector"]:
                        final_type = bt + "(" + str(wd - 1) + ":0)"
            e = EntityBlock(cvs, 100, 100, nm, [], [{"name":nm, "dir":dr, "type":final_type}], True)
            cvs.data["blocks"].append(e)
            w.destroy()
        tk.Button(w, text="Create", command=ok).pack()

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
        "active_port": None,
        "project_root": directory
    }
    canvas.data["create_adapter_cb"] = lambda mx,my,a,b,sp,cp,old_line,color: create_adapter(canvas, mx,my,a,b,sp,cp,old_line,color)

    load_previous_configuration(canvas, os.path.join(directory, "TopLevelAdapter.json"))

    def start_drag(e):
        s = blocks_listbox.curselection()
        if s:
            i = s[0]
            it = blocks_listbox.get(i)
            block_info = it.split(": ")
            if len(block_info) == 2:
                bt, bn = block_info
                selected_block = next((b_ for b_ in blocks if b_[0] == bn), None)
                if selected_block:
                    canvas.data["drag_block"] = selected_block
                    canvas.data["drag_label"] = tk.Label(left_frame, text=bn, bg="lightgreen")
                    canvas.data["drag_label"].place(x=e.x, y=e.y)
                    blocks_listbox.bind("<Motion>", on_drag_motion)
                    blocks_listbox.bind("<ButtonRelease-1>", on_drag_release)

    def on_drag_motion(e):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].place(x=e.x, y=e.y)

    def on_drag_release(e):
        if "drag_label" in canvas.data:
            canvas.data["drag_label"].destroy()
            del canvas.data["drag_label"]
            block = canvas.data.get("drag_block")
            if block:
                cx = canvas.winfo_pointerx() - canvas.winfo_rootx() - right_frame.winfo_x()
                cy = canvas.winfo_pointery() - canvas.winfo_rooty() - right_frame.winfo_y()
                if 0 <= cx <= canvas.winfo_width() and 0 <= cy <= canvas.winfo_height():
                    name, generics, ports = block
                    if not generics and not ports:
                        tk.messagebox.showinfo("Info", "Block '" + name + "' has no generics or ports.")
                    else:
                        eb = EntityBlock(canvas, cx, cy, name, generics, ports, conduit=False)
                        canvas.data["blocks"].append(eb)
            del canvas.data["drag_block"]
            blocks_listbox.unbind("<Motion>")
            blocks_listbox.unbind("<ButtonRelease-1>")

    blocks_listbox.bind("<Button-1>", start_drag)
    root.mainloop()
