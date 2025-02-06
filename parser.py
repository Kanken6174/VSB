#parser.py
import os
import re

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
