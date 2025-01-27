# utils.py
import re

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

def extract_width(vtype):
    def parse_vhdl_range(s):
        m = re.search(r"\((\d+)\s*(downto|to|:)\s*(\d+)\)", s, re.IGNORECASE)
        if m:
            try:
                upper = int(m.group(1))
                lower = int(m.group(3))
                return abs(upper - lower) + 1
            except:
                return None
        return None

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
            if a["width"] == b["width"]:
                return True
            else:
                return False
        if a["kind"] == "INTEGER":
            return True
    return False
