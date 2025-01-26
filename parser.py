# parser.py
import os
import re

DEBUG = True

def preprocess_vhdl(text):
    lines = text.split('\n')
    out = []
    for line in lines:
        idx = line.find('--')
        if idx != -1:
            line = line[:idx]
        out.append(line)
    return '\n'.join(out)

def extract_ports(block):
    block = block.strip().replace('\n', ' ').replace('\r', ' ')
    if not block.endswith(';'):
        block += ';'
    items = re.split(r';', block)
    ports = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        m = re.match(r"([\w\d_]+)\s*:\s*(in|out|inout)\s+(.+)$", item, re.IGNORECASE)
        if m:
            nm = m.group(1).strip()
            dr = m.group(2).lower().strip()
            tp = m.group(3).strip().rstrip(',')
            ports.append({"name": nm, "dir": dr, "type": tp})
    return ports

def parse_vhdl_for_entities(text):
    text = preprocess_vhdl(text)
    entity_pattern = r"entity\s+([\w\d_]+)\s+is\s+(.*?)end\s+\1\s*;"
    found = re.findall(entity_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    out = []
    
    for enName, enBody in found:
        port_pattern = r"port\s*\(\s*(.*)\s*\)\s*;"
        pm = re.search(port_pattern, enBody, flags=re.DOTALL | re.IGNORECASE)
        ports = []
        
        if pm:
            block = pm.group(1)
            if DEBUG:
                print(f"Entity '{enName}' Ports Block:\n{block}\n")
            ports = extract_ports(block)
        
        out.append((enName, ports))
    
    return out

def scan_file(path):
    if DEBUG:
        print("Scanning file:", path)
    with open(path, "r") as f:
        content = f.read()
    return parse_vhdl_for_entities(content)

def find_entities(directory):
    if DEBUG:
        print("Finding entities in directory:", directory)
    entities = []
    if not os.path.isdir(directory):
        return entities
    for filename in os.listdir(directory):
        lower_filename = filename.lower()
        if (lower_filename.endswith(".vhd") or lower_filename.endswith(".vhdl")) and \
           not lower_filename.startswith("tb_") and \
           not lower_filename.endswith("_tb.vhd") and \
           not lower_filename.endswith("_tb.vhdl"):
            filepath = os.path.join(directory, filename)
            parsed = scan_file(filepath)
            entities.extend(parsed)
    
    ip_dir = os.path.join(directory, "ip")
    if os.path.isdir(ip_dir):
        for root_dir, dirs, files in os.walk(ip_dir):
            for file in files:
                lower_file = file.lower()
                if (lower_file.endswith(".vhd") or lower_file.endswith(".vhdl")) and \
                   not lower_file.startswith("tb_") and \
                   not lower_file.endswith("_tb.vhd") and \
                   not lower_file.endswith("_tb.vhdl"):
                    filepath = os.path.join(root_dir, file)
                    parsed = scan_file(filepath)
                    entities.extend(parsed)
    return entities

def parse_vhdl_range(s):
    """
    Parses the range in a VHDL type declaration and returns the width.
    Supports 'downto', 'to', and ':' operators.

    Examples:
        'std_logic_vector(5 downto 0)' -> 6
        'std_logic_vector(0 to 5)'    -> 6
        'std_logic_vector(5:0)'       -> 6
    """
    m = re.search(r"\((\d+)\s*(downto|to|:)\s*(\d+)\)", s, re.IGNORECASE)
    if m:
        try:
            upper = int(m.group(1))
            lower = int(m.group(3))
            return abs(upper - lower) + 1
        except:
            return None
    return None

def extract_width(vtype):
    st = vtype.lower().strip()
    if "std_logic" in st:
        if "vector" in st:
            w = parse_vhdl_range(st)
            return w if w else None
        else:
            return 1
    if "signed" in st or "unsigned" in st:
        w = parse_vhdl_range(st)
        return w if w else None
    if "integer" in st:
        return None
    return None

def extract_kind(vtype):
    s = vtype.lower().strip()
    if "std_logic" in s:
        if "vector" in s:
            return "SLV"
        else:
            return "SL"
    if "signed" in s:
        return "SIGNED"
    if "unsigned" in s:
        return "UNSIGNED"
    if "integer" in s:
        return "INTEGER"
    return "OTHER"

def check_dir(d1, d2):
    if d1 == "out" and d2 in ["in", "inout"]:
        return True
    if d1 == "in" and d2 in ["out", "inout"]:
        return True
    if d1 == "inout" and d2 in ["in", "out", "inout"]:
        return True
    return False

def types_compatible(a, b):
    if a["kind"] == b["kind"]:
        if a["kind"] in ["SL", "OTHER"]:
            return True
        if a["kind"] in ["SLV", "SIGNED", "UNSIGNED"]:
            if a["width"] is None or b["width"] is None:
                return False
            return a["width"] == b["width"]
        if a["kind"] == "INTEGER":
            return True
    return False
