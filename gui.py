#gui.py
import tkinter as tk
import os
import json
from vhdl_parser import find_blocks, parse_peri_xml
from entity_block import EntityBlock
from generator import generate_top_level

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
        if t == "adapter":
            continue
        n = bd["name"]
        x = bd["x"]
        y = bd["y"]
        if t == "entity":
            g = bd.get("generics", [])
            ps = bd.get("ports", [])
            ep = []
            for p_ in ps:
                ep.append({
                    "name": p_["port_name"],
                    "dir":  p_["port_dir"],
                    "type": p_["port_type"]
                })
            e = EntityBlock(canvas, x, y, n, g, ep, bd.get("conduit", False))
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
            for i, pps in enumerate(e.port_symbols):
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
                    canvas.itemconfig(pps.id, fill="black", outline="red")
                else:
                    if pps.port["dir"] in ["out", "inout"]:
                        pps.color = ps[i].get("color")
                        if pps.color:
                            canvas.itemconfig(pps.id, fill=pps.color, outline=pps.color)
            nb.append(e)
    canvas.data["blocks"].extend(nb)
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
            ln = canvas.create_line(
                pp1.x, pp1.y, pp2.x, pp2.y,
                fill=pp1.color if pp1.color else "black",
                tags=("wire",),
                smooth=True, splinesteps=36, width=3
            )
            canvas.data["connections"].append((pp1, pp2, ln, None))
            cx1 = pp1.x + (pp2.x - pp1.x) / 2
            cy1 = pp1.y
            cx2 = pp1.x + (pp2.x - pp1.x) / 2
            cy2 = pp2.y
            canvas.coords(ln, pp1.x, pp1.y, cx1, cy1, cx2, cy2, pp2.x, pp2.y)
    for w in canvas.find_withtag("wire"):
        canvas.tag_bind(w, "<Button-3>", lambda e: wire_right_click(e, canvas))

def add_board_io(canvas, input_side, output_side):
    if "board_io_created" in canvas.data and canvas.data["board_io_created"]:
        return
    canvas.data["board_io_created"] = True
    b_in_ports = []
    for p in input_side:
        if p["dir"] == "in":
            b_in_ports.append({"name": p["name"], "dir": "out", "type": p["type"]})
        else:
            b_in_ports.append({"name": p["name"], "dir": p["dir"], "type": p["type"]})

    b_out_ports = []
    for p in output_side:
        if p["dir"] == "out":
            b_out_ports.append({"name": p["name"], "dir": "in", "type": p["type"]})
        else:
            b_out_ports.append({"name": p["name"], "dir": p["dir"], "type": p["type"]})

    b_in = EntityBlock(canvas, 50, 50, "BoardInputs", [], b_in_ports, conduit=True)
    b_out = EntityBlock(canvas, 250, 50, "BoardOutputs", [], b_out_ports, conduit=True)
    canvas.data["blocks"].append(b_in)
    canvas.data["blocks"].append(b_out)

def run_gui(directory):
    blocks = find_blocks(directory)
    in_signals, out_signals = parse_peri_xml(directory)
    root = tk.Tk()
    root.title("Efinix System Builder")
    left_frame = tk.Frame(root)
    left_frame.pack(side="left", fill="y", padx=5, pady=5)
    tk.Label(left_frame, text="Available Blocks").pack()
    blocks_listbox = tk.Listbox(left_frame)
    blocks_listbox.pack(fill="both", expand=True)
    for b in blocks:
        nm, gen, pts = b
        blocks_listbox.insert("end",("Empty Block: " if not gen and not pts else "Entity/Component: ")+nm)

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
                    tk.messagebox.showerror("Error", "Conduit '"+nm+"' already exists.")
                    return
            final_type = bt
            if wd.isdigit():
                wd = int(wd)
                if wd <= 1:
                    if bt.lower() in ["std_logic_vector", "signed", "unsigned", "std_logic"]:
                        final_type = "std_logic"
                else:
                    if bt.lower() == "std_logic":
                        final_type = f"std_logic_vector({wd - 1} downto 0)"
                    elif bt.lower() in ["signed", "unsigned", "std_logic_vector"]:
                        final_type = f"{bt}({wd - 1} downto 0)"
            final_dir = "out" if dr=="in" else ("in" if dr=="out" else "inout")
            e = EntityBlock(cvs, 100, 100, nm, [], [{"name": nm, "dir": final_dir,"type": final_type}], True)
            cvs.data["blocks"].append(e)
            w.destroy()
        tk.Button(w, text="Create", command=ok).pack()

    load_previous_configuration_button = tk.Button(left_frame, text="Load Existing (if any)", command=lambda: load_previous_configuration(canvas, os.path.join(directory,"Main.json")))
    load_previous_configuration_button.pack(pady=5, fill="x")
    add_conduit_button = tk.Button(left_frame, text="New Conduit", command=lambda: add_conduit(root, canvas))
    add_conduit_button.pack(pady=5, fill="x")
    add_board_io_button = tk.Button(left_frame, text="Add Board IO", command=lambda: add_board_io(canvas, in_signals, out_signals))
    add_board_io_button.pack(pady=5, fill="x")
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
                cx = canvas.canvasx(e.x)
                cy = canvas.canvasy(e.y)
                if 0 <= cx <= canvas.winfo_width() and 0 <= cy <= canvas.winfo_height():
                    name, generics, ports = block
                    if not generics and not ports:
                        tk.messagebox.showinfo("Info", f"Block '{name}' has no generics or ports.")
                    else:
                        eblock = EntityBlock(canvas, cx, cy, name, generics, ports, conduit=False)
                        canvas.data["blocks"].append(eblock)
            del canvas.data["drag_block"]
            blocks_listbox.unbind("<Motion>")
            blocks_listbox.unbind("<ButtonRelease-1>")

    blocks_listbox.bind("<Button-1>", start_drag)

    def on_pan_start(event):
        canvas.scan_mark(event.x, event.y)

    def on_pan_move(event):
        canvas.scan_dragto(event.x, event.y, gain=1)

    canvas.bind("<ButtonPress-2>", on_pan_start)
    canvas.bind("<B2-Motion>", on_pan_move)
    load_previous_configuration(canvas, os.path.join(directory, "Main.json"))
    root.mainloop()
