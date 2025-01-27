# parser.py
import os
import re
from collections import defaultdict
from utils import extract_kind, extract_width, check_dir, types_compatible

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

def extract_generics(block):
    block = block.strip().replace('\n', ' ').replace('\r', ' ')
    if not block.endswith(';'):
        block += ';'
    items = re.split(r';', block)
    generics = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        m = re.match(r"([\w\d_]+)\s*:\s*(\w+)\s*(?::=\s*([^;]+))?$", item, re.IGNORECASE)
        if m:
            nm = m.group(1).strip()
            tp = m.group(2).strip()
            default = m.group(3).strip() if m.group(3) else None
            generics.append({"name": nm, "type": tp, "default": default})
    return generics

def parse_vhdl_for_entities(text):
    text = preprocess_vhdl(text)
    entity_pattern = r"entity\s+([\w\d_]+)\s+is\s+(.*?)end\s+\1\s*;"
    found = re.findall(entity_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    out = []
    
    for enName, enBody in found:
        generic_pattern = r"generic\s*\(\s*(.*?)\s*\)\s*;"
        pm_gen = re.search(generic_pattern, enBody, flags=re.DOTALL | re.IGNORECASE)
        generics = []
        
        if pm_gen:
            block_gen = pm_gen.group(1)
            if DEBUG:
                print(f"Entity '{enName}' Generics Block:\n{block_gen}\n")
            generics = extract_generics(block_gen)
        
        port_pattern = r"port\s*\(\s*(.*)\s*\)\s*;"
        pm_port = re.search(port_pattern, enBody, flags=re.DOTALL | re.IGNORECASE)
        ports = []
        
        if pm_port:
            block_port = pm_port.group(1)
            if DEBUG:
                print(f"Entity '{enName}' Ports Block:\n{block_port}\n")
            ports = extract_ports(block_port)
        
        out.append((enName, generics, ports))
    
    return out

def parse_vhdl_for_components(text):
    text = preprocess_vhdl(text)
    component_pattern = r"COMPONENT\s+([\w\d_]+)\s+is\s+(.*?)END\s+COMPONENT\s*;"
    found = re.findall(component_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    out = []
    
    for compName, compBody in found:
        port_pattern = r"PORT\s*\(\s*(.*)\s*\)\s*;"
        pm_port = re.search(port_pattern, compBody, flags=re.DOTALL | re.IGNORECASE)
        ports = []
        
        if pm_port:
            block_port = pm_port.group(1)
            if DEBUG:
                print(f"Component '{compName}' Ports Block:\n{block_port}\n")
            ports = extract_ports(block_port)
        
        out.append((compName, [], ports))
    
    return out

def scan_file(path):
    if DEBUG:
        print("Scanning file:", path)
    with open(path, "r") as f:
        content = f.read()
    entities = parse_vhdl_for_entities(content)
    components = parse_vhdl_for_components(content)
    return entities, components

def find_blocks(directory):
    if DEBUG:
        print("Finding blocks in directory:", directory)
    blocks_dict = {}
    if not os.path.isdir(directory):
        return []
    for filename in os.listdir(directory):
        lower_filename = filename.lower()
        if (lower_filename.endswith(".vhd") or lower_filename.endswith(".vhdl")) and \
           not lower_filename.startswith("tb_") and \
           not lower_filename.endswith("_tb.vhd") and \
           not lower_filename.endswith("_tb.vhdl"):
            filepath = os.path.join(directory, filename)
            parsed_entities, parsed_components = scan_file(filepath)
            for name, generics, ports in parsed_entities:
                if name in blocks_dict:
                    existing_generics = blocks_dict[name][1]
                    existing_ports = blocks_dict[name][2]
                    for gen in generics:
                        if not any(g['name'] == gen['name'] for g in existing_generics):
                            existing_generics.append(gen)
                    for port in ports:
                        if not any(p['name'] == port['name'] for p in existing_ports):
                            existing_ports.append(port)
                else:
                    blocks_dict[name] = (name, generics.copy(), ports.copy())
            for name, generics, ports in parsed_components:
                if name in blocks_dict:
                    existing_generics = blocks_dict[name][1]
                    existing_ports = blocks_dict[name][2]
                    for port in ports:
                        if not any(p['name'] == port['name'] for p in existing_ports):
                            existing_ports.append(port)
                else:
                    blocks_dict[name] = (name, generics.copy(), ports.copy())
    
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
                    parsed_entities, parsed_components = scan_file(filepath)
                    for name, generics, ports in parsed_entities:
                        if name in blocks_dict:
                            existing_generics = blocks_dict[name][1]
                            existing_ports = blocks_dict[name][2]
                            for gen in generics:
                                if not any(g['name'] == gen['name'] for g in existing_generics):
                                    existing_generics.append(gen)
                            for port in ports:
                                if not any(p['name'] == port['name'] for p in existing_ports):
                                    existing_ports.append(port)
                        else:
                            blocks_dict[name] = (name, generics.copy(), ports.copy())
                    for name, generics, ports in parsed_components:
                        if name in blocks_dict:
                            existing_generics = blocks_dict[name][1]
                            existing_ports = blocks_dict[name][2]
                            for port in ports:
                                if not any(p['name'] == port['name'] for p in existing_ports):
                                    existing_ports.append(port)
                        else:
                            blocks_dict[name] = (name, generics.copy(), ports.copy())
    
    unique_blocks = list(blocks_dict.values())
    return unique_blocks
