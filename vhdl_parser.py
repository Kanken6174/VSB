#vhdl_parser.py
import os
import re
import xml.etree.ElementTree as ET

def preprocess_vhdl(t):
    lines = t.split('\n')
    r = []
    for l in lines:
        i = l.find('--')
        if i != -1:
            l = l[:i]
        r.append(l)
    return '\n'.join(r)

def extract_ports(b):
    b = b.strip().replace('\n',' ').replace('\r',' ')
    if not b.endswith(';'):
        b += ';'
    items = re.split(r';', b)
    ports = []
    for it in items:
        it = it.strip()
        if not it:
            continue
        m = re.match(r"([\w\d_]+)\s*:\s*(in|out|inout)\s+(.+)$", it, re.IGNORECASE)
        if m:
            nm = m.group(1).strip()
            dr = m.group(2).lower().strip()
            tp = m.group(3).strip().rstrip(',')
            ports.append({"name":nm,"dir":dr,"type":tp})
    return ports

def extract_generics(b):
    b = b.strip().replace('\n',' ').replace('\r',' ')
    if not b.endswith(';'):
        b += ';'
    items = re.split(r';', b)
    gens = []
    for it in items:
        it = it.strip()
        if not it:
            continue
        m = re.match(r"([\w\d_]+)\s*:\s*(\w+)\s*(?::=\s*([^;]+))?$", it, re.IGNORECASE)
        if m:
            nm = m.group(1).strip()
            tp = m.group(2).strip()
            d  = m.group(3).strip() if m.group(3) else None
            gens.append({"name":nm,"type":tp,"default":d})
    return gens

def parse_vhdl_for_entities(t):
    txt = preprocess_vhdl(t)
    p = r"entity\s+([\w\d_]+)\s+is\s+(.*?)end\s+\1\s*;"
    found = re.findall(p, txt, flags=re.DOTALL|re.IGNORECASE)
    out = []
    for en, bd in found:
        gp = re.search(r"generic\s*\(\s*(.*?)\s*\)\s*;", bd, flags=re.DOTALL|re.IGNORECASE)
        gs = []
        if gp:
            gs = extract_generics(gp.group(1))
        pp = re.search(r"port\s*\(\s*(.*)\s*\)\s*;", bd, flags=re.DOTALL|re.IGNORECASE)
        ps = []
        if pp:
            ps = extract_ports(pp.group(1))
        out.append((en, gs, ps))
    return out

def parse_vhdl_for_components(t):
    txt = preprocess_vhdl(t)
    p = r"COMPONENT\s+([\w\d_]+)\s+is\s+(.*?)END\s+COMPONENT(?:\s+\1)?\s*;"
    found = re.findall(p, txt, flags=re.DOTALL|re.IGNORECASE)
    out = []
    for cn, bd in found:
        pm_port = re.search(r"PORT\s*\(\s*(.*)\s*\)\s*;", bd, flags=re.DOTALL|re.IGNORECASE)
        ports = []
        if pm_port:
            ports = extract_ports(pm_port.group(1))
        out.append((cn, [], ports))
    return out

def scan_file(pa):
    with open(pa, "r") as ff:
        c = ff.read()
    e = parse_vhdl_for_entities(c)
    co = parse_vhdl_for_components(c)
    return e, co

def find_blocks(d):
    bd = {}
    if not os.path.isdir(d):
        return []
    for fn in os.listdir(d):
        lf = fn.lower()
        if (lf.endswith(".vhd") or lf.endswith(".vhdl")) and \
           not lf.startswith("tb_") and \
           not lf.endswith("_tb.vhd") and \
           not lf.endswith("_tb.vhdl") and \
           not lf.endswith("topleveladapter.vhd"):
            fp = os.path.join(d, fn)
            pe, pc = scan_file(fp)
            for name, g, p in pe:
                if name in bd:
                    eg = bd[name][1]
                    ep = bd[name][2]
                    for gg in g:
                        if not any(x['name'] == gg['name'] for x in eg):
                            eg.append(gg)
                    for pp in p:
                        if not any(x['name'] == pp['name'] for x in ep):
                            ep.append(pp)
                else:
                    bd[name] = (name, g.copy(), p.copy())
            for name, g, p in pc:
                if name in bd:
                    eg = bd[name][1]
                    ep = bd[name][2]
                    for pp in p:
                        if not any(x['name'] == pp['name'] for x in ep):
                            ep.append(pp)
                else:
                    bd[name] = (name, g.copy(), p.copy())
    ipd = os.path.join(d, "ip")
    if os.path.isdir(ipd):
        for root, dirs, files in os.walk(ipd):
            for fl in files:
                lfl = fl.lower()
                if (lfl.endswith(".vhd") or lfl.endswith(".vhdl")) and \
                   not lfl.startswith("tb_") and \
                   not lfl.endswith("_tb.vhd") and \
                   not lfl.endswith("_tb.vhdl"):
                    fp = os.path.join(root, fl)
                    pe, pc = scan_file(fp)
                    for name, g, p in pe:
                        if name in bd:
                            eg = bd[name][1]
                            ep = bd[name][2]
                            for gg in g:
                                if not any(x['name'] == gg['name'] for x in eg):
                                    eg.append(gg)
                            for pp in p:
                                if not any(x['name'] == pp['name'] for x in ep):
                                    ep.append(pp)
                        else:
                            bd[name] = (name, g.copy(), p.copy())
                    for name, g, p in pc:
                        if name in bd:
                            eg = bd[name][1]
                            ep = bd[name][2]
                            for pp in p:
                                if not any(x['name'] == pp['name'] for x in ep):
                                    ep.append(pp)
                        else:
                            bd[name] = (name, g.copy(), p.copy())
    return list(bd.values())

def parse_gpio_name(name):
    m = re.match(r"(.*)\[(\d+)\]$", name)
    if m:
        return m.group(1), int(m.group(2))
    return name, None

def produce_port_entry(base_name, idx_list, direction):
    if len(idx_list) == 1:
        return {"name": f"{base_name}", "dir": direction, "type": "std_logic"}
    else:
        hi = max(idx_list)
        lo = min(idx_list)
        return {"name": base_name, "dir": direction, "type": f"std_logic_vector({hi} downto {lo})"}

def parse_peri_xml(d):
    path = os.path.join(d, "DIspx.peri.xml")
    if not os.path.exists(path):
        return [], []
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {'efxpt': 'http://www.efinixinc.com/peri_design_db'}

    gps = root.findall('.//efxpt:gpio', ns)
    input_bus_map = {}
    output_bus_map = {}
    inout_individual = []

    for gp in gps:
        n = gp.get('name','')
        m = gp.get('mode','').lower()
        if m == 'inout':
            read_base, read_idx = parse_gpio_name(n+"_read")
            write_base, write_idx = parse_gpio_name(n+"_write")
            en_base, en_idx = parse_gpio_name(n+"_writeEnable")
            inout_individual.append({"name": read_base, "idx": read_idx, "dir": "in"})
            inout_individual.append({"name": write_base, "idx": write_idx, "dir": "out"})
            inout_individual.append({"name": en_base, "idx": en_idx, "dir": "out"})
        else:
            base, idx = parse_gpio_name(n)
            if m == 'input':
                bus_map = input_bus_map
                direct = 'in'
            else:
                bus_map = output_bus_map
                direct = 'out'
            if base not in bus_map:
                bus_map[base] = {"dir": direct, "idx_set": set()}
            bus_map[base]["idx_set"].add(idx if idx is not None else -1)

    in_list = []
    out_list = []

    for k,info in input_bus_map.items():
        direct = info["dir"]
        idxs = sorted([x for x in info["idx_set"]])
        if idxs == [-1]:
            in_list.append({"name": k,"dir": direct,"type":"std_logic"})
        else:
            hi = max(idxs)
            lo = min(idxs)
            if hi == lo:
                in_list.append({"name": k,"dir": direct,"type":"std_logic"})
            else:
                in_list.append({
                    "name": k,
                    "dir": direct,
                    "type": f"std_logic_vector({hi} downto {lo})"
                })

    for k,info in output_bus_map.items():
        direct = info["dir"]
        idxs = sorted([x for x in info["idx_set"]])
        if idxs == [-1]:
            out_list.append({"name": k,"dir": direct,"type":"std_logic"})
        else:
            hi = max(idxs)
            lo = min(idxs)
            if hi == lo:
                out_list.append({"name": k,"dir": direct,"type":"std_logic"})
            else:
                out_list.append({
                    "name": k,
                    "dir": direct,
                    "type": f"std_logic_vector({hi} downto {lo})"
                })

    inout_in = []
    inout_out = []
    for x in inout_individual:
        if x["dir"] == "in":
            inout_in.append({"name": x["name"], "dir":"in","type":"std_logic"})
        else:
            inout_out.append({"name": x["name"], "dir":"out","type":"std_logic"})

    board_in = in_list + inout_in
    board_out = out_list + inout_out

    # Parse PLL outputs as additional "inputs" to the core.
    pll_list = root.findall('.//efxpt:pll', ns)
    for pll in pll_list:
        outs = pll.findall('.//efxpt:output_clock', ns)
        for oc in outs:
            clk_name = oc.get('name','')
            # We'll treat these PLL outputs as additional "inputs" from the board's perspective
            if clk_name:
                board_in.append({"name": clk_name, "dir":"in", "type":"std_logic"})

    return board_in, board_out
