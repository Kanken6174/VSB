import re

def extract_kind(v):
    s=v.lower().strip()
    if "std_logic" in s:
        if "vector" in s:
            return "SLV"
        return "SL"
    if "signed" in s:
        return "SIGNED"
    if "unsigned" in s:
        return "UNSIGNED"
    if "integer" in s:
        return "INTEGER"
    return "OTHER"

def extract_width(v):
    m=re.search(r"\((\d+)\s*(?:downto|to|:)\s*(\d+)\)",v,re.IGNORECASE)
    if m:
        try:
            u=int(m.group(1))
            l=int(m.group(2))
            return abs(u-l)+1
        except:
            return None
    if "std_logic" in v.lower() and "vector" not in v.lower():
        return 1
    return None

def check_dir(d1,d2):
    if d1=="out" and d2 in ["in","inout"]:
        return True
    if d1=="in" and d2 in ["out","inout"]:
        return True
    if d1=="inout" and d2 in ["in","out","inout"]:
        return True
    return False

def types_compatible(a,b):
    ka=a["kind"].lower()
    kb=b["kind"].lower()
    if ka==kb:
        if ka in ["sl","other"]:
            return True
        if ka in ["slv","signed","unsigned"]:
            return a.get("width")==b.get("width")
        if ka=="integer":
            return True
    return False
