#generator.py
import os
import re
import json
from collections import defaultdict
from entity_block import EntityBlock
from utils import extract_width

def flip_direction(d):
    if d == "in":
        return "out"
    if d == "out":
        return "in"
    return d

def get_default_assignment(v):
    s = v.lower()
    m = re.search(r'\((\d+)\s*downto\s*(\d+)\)', s)
    if not m:
        m = re.search(r'\((\d+):0\)', s)
    if "std_logic_vector" in s or "signed" in s or "unsigned" in s:
        if m:
            hi = int(m.group(1))
            lo = int(m.group(2))
            w = abs(hi - lo) + 1
            return "(others => '0')" if w > 1 else "'0'"
        return "(others => '0')"
    if "std_logic" in s:
        return "'0'"
    if "integer" in s:
        return "0"
    return "'0'"

def generate_top_level(canvas):
    r = canvas.data.get("project_root", ".")
    os.makedirs(r, exist_ok=True)
    p = os.path.join(r, "Main.vhd")
    b = canvas.data["blocks"]
    c = canvas.data["connections"]
    cb = [x for x in b if getattr(x, 'conduit', False)]
    cp = []
    for x in b:
        for y in x.port_symbols:
            if getattr(y, "is_conduit", False):
                cp.append(y)

    tin = [pt for xx in cb for pt in xx.port_symbols if pt.port["dir"] in ["in", "inout"]]
    tout = [pt for xx in cb for pt in xx.port_symbols if pt.port["dir"] in ["out", "inout"]]
    tin += [pt for pt in cp if pt.port["dir"] in ["in", "inout"]]
    tout += [pt for pt in cp if pt.port["dir"] in ["out", "inout"]]

    parent = {}
    for x_ in b:
        for y_ in x_.port_symbols:
            parent[y_] = y_

    def fnd(p):
        if parent[p] != p:
            parent[p] = fnd(parent[p])
        return parent[p]

    def un(p, q):
        rp = fnd(p)
        rq = fnd(q)
        if rp != rq:
            parent[rq] = rp

    for x_ in c:
        p1, p2, _, _ = x_
        un(p1, p2)

    groups = defaultdict(list)
    for x_ in b:
        for y_ in x_.port_symbols:
            root = fnd(y_)
            groups[root].append(y_)

    sn = {}
    sc = 1
    for v_ in groups.values():
        i = [x_ for x_ in v_ if x_ in tin]
        o = [x_ for x_ in v_ if x_ in tout]
        if i and o:
            s = f"sig{sc}"
            sc += 1
            for x_ in v_:
                sn[x_] = s
        elif i:
            s = i[0].port["name"]
            for x_ in v_:
                sn[x_] = s
        elif o:
            s = o[0].port["name"]
            for x_ in v_:
                sn[x_] = s
        else:
            s = f"sig{sc}"
            sc += 1
            for x_ in v_:
                sn[x_] = s

    top_level_signal_names = set(pt.port["name"] for xx in cb for pt in xx.port_symbols)
    top_level_signal_names.update(pt.port["name"] for pt in cp)
    internal_signals = set(sn.values()) - top_level_signal_names

    with open(p, "w") as f:
        f.write("library ieee;\nuse ieee.std_logic_1164.all;\nuse ieee.numeric_std.all;\n\n")
        f.write("entity Main is\n")
        f.write("    port(\n")
        unique_ports = {}
        all_conduits = [pt for xx in cb for pt in xx.port_symbols if getattr(xx, 'conduit', False)] + cp
        for pt in all_conduits:
            pname = pt.port['name']
            if pname not in unique_ports:
                if isinstance(pt.block, EntityBlock) and getattr(pt.block, 'conduit', False):
                    od = flip_direction(pt.port["dir"])
                else:
                    od = pt.port["dir"]
                unique_ports[pname] = (pname, od, pt.port["type"])
    
        def normalize_type(ptype):
            if "std_logic_vector" in ptype.lower():
                w = extract_width(ptype)
                if w == 1:
                    return "std_logic"
            return ptype
    
        up_keys = list(unique_ports.keys())
        for i, key in enumerate(up_keys):
            pname, odir, ptype = unique_ports[key]
            ptype = normalize_type(ptype)
            line = f"        {pname} : {odir} {ptype}"
            if i < len(up_keys) - 1:
                line += ";"
            f.write(line + "\n")
        f.write("    );\n")
        f.write("end Main;\n\n")
        f.write("architecture Behavioral of Main is\n")
        if internal_signals:
            for sg in internal_signals:
                match_ps = [pp for (pp, nm) in sn.items() if nm == sg]
                if match_ps:
                    vtype = normalize_type(match_ps[0].port["type"])
                    f.write(f"    signal {sg} : {vtype};\n")
            f.write("\n")
        comp_ports = defaultdict(list)
        comp_gens = defaultdict(list)
        for x_ in b:
            if getattr(x_, "conduit", False):
                continue
            if isinstance(x_, EntityBlock):
                comp_ports[x_.name].extend(p_.port for p_ in x_.port_symbols)
                if x_.generics:
                    comp_gens[x_.name].extend(x_.generics)
        for comp, prts in comp_ports.items():
            f.write(f"    component {comp} is\n")
            if comp_gens[comp]:
                f.write("        generic(\n")
                for i, g_ in enumerate(comp_gens[comp]):
                    line = f"            {g_['name']} : {g_['type']}"
                    if g_.get("default"):
                        line += f" := {g_['default']}"
                    if i < len(comp_gens[comp]) - 1:
                        line += ";"
                    f.write(line + "\n")
                f.write("        );\n")
            f.write("        port(\n")
            for i, p_ in enumerate(prts):
                line = f"            {p_['name']} : {p_['dir']} {p_['type']}"
                if i < len(prts) - 1:
                    line += ";"
                f.write(line + "\n")
            f.write("        );\n")
            f.write(f"    end component;\n\n")
        f.write("begin\n\n")
        instance_count = defaultdict(int)
        for blk in b:
            if getattr(blk, "conduit", False):
                continue
            instance_count[blk.name] += 1
            idx = instance_count[blk.name] - 1
            iname = f"{blk.name}_inst{idx}" if instance_count[blk.name] > 1 else f"{blk.name}_inst"
            if blk.generics:
                f.write(f"    {iname} : {blk.name} generic map(\n")
                gm = []
                for g_ in blk.generics:
                    gn = g_["name"]
                    gv = blk.generic_values.get(gn, g_.get("default"))
                    if isinstance(gv, str) and not (gv.startswith("'") or gv.startswith('"')):
                        gv = f'"{gv}"'
                    gm.append(f"        {gn} => {gv}")
                f.write(",\n".join(gm))
                f.write("\n    ) port map(\n")
            else:
                f.write(f"    {iname} : {blk.name} port map(\n")
            lines_map = []
            for ps_ in blk.port_symbols:
                pn = ps_.port['name']
                if "std_logic_vector" in ps_.port["type"].lower():
                    w = extract_width(ps_.port["type"])
                    if w == 1:
                        comp_port_name = f"{pn}(0)"
                    else:
                        comp_port_name = pn
                else:
                    comp_port_name = pn

                if ps_ in sn:
                    lines_map.append(f"        {comp_port_name} => {sn[ps_]}")
                else:
                    if ps_.port["dir"] in ["in", "inout"]:
                        df = get_default_assignment(ps_.port["type"])
                        lines_map.append(f"        {comp_port_name} => {df}")
                    else:
                        lines_map.append(f"        {comp_port_name} => open")
            f.write(",\n".join(lines_map))
            f.write("\n    );\n\n")
        f.write("end Behavioral;\n")
    out_json = {}
    out_json["blocks"] = []
    for block in b:
        if hasattr(block, "mode"):
            continue
        bd = {}
        bd["type"] = "entity"
        bd["name"] = block.name
        bd["x"] = block.x
        bd["y"] = block.y
        if hasattr(block, "conduit"):
            bd["conduit"] = block.conduit
        if hasattr(block, "generics"):
            bd["generics"] = block.generics
            bd["generic_values"] = getattr(block, "generic_values", {})
        ports_arr = []
        for ps_ in block.port_symbols:
            p_js = {}
            p_js["port_name"] = ps_.port["name"]
            p_js["port_dir"] = ps_.port["dir"]
            p_js["port_type"] = ps_.port["type"]
            p_js["x"] = ps_.x
            p_js["y"] = ps_.y
            p_js["is_conduit"] = getattr(ps_, "is_conduit", False)
            if ps_.port["dir"] in ["out", "inout"]:
                p_js["color"] = ps_.color if ps_.color else None
            ports_arr.append(p_js)
        bd["ports"] = ports_arr
        out_json["blocks"].append(bd)
    out_json["connections"] = []
    for c_ in c:
        p1, p2, _, _ = c_
        out_json["connections"].append({
            "block1": p1.block.name,
            "block2": p2.block.name,
            "port1": p1.port["name"],
            "port2": p2.port["name"]
        })
    with open(os.path.join(r, "Main.json"), "w") as jf:
        json.dump(out_json, jf, indent=2)
