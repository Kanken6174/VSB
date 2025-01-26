# generator.py
import os
from collections import defaultdict
from gui_components import AdapterBlock
import re

def generate_top_level(canvas):
    adapters_dir = "Adapters"
    os.makedirs(adapters_dir, exist_ok=True)
    filepath = os.path.join(adapters_dir, "TopLevelAdapter.vhd")
    
    blocks = canvas.data["blocks"]
    connections = canvas.data["connections"]
    
    conduits = [block for block in blocks if block.conduit]
    top_level_ports = []
    for conduit in conduits:
        for port in conduit.port_symbols:
            top_level_ports.append(port)
    
    parent = {}
    for block in blocks:
        for port in block.port_symbols:
            parent[port] = port
    
    def find(p):
        if parent[p] != p:
            parent[p] = find(parent[p])
        return parent[p]
    
    def union(p, q):
        root_p = find(p)
        root_q = find(q)
        if root_p != root_q:
            parent[root_q] = root_p
    
    for connection in connections:
        port1, port2, line, adapter = connection
        union(port1, port2)
    
    groups = defaultdict(list)
    for block in blocks:
        for port in block.port_symbols:
            root = find(port)
            groups[root].append(port)
    
    signal_names = {}
    signal_counter = 1
    for group_ports in groups.values():
        if len(group_ports) > 1:
            conduit_ports = [p for p in group_ports if p in top_level_ports]
            if conduit_ports:
                signal_name = conduit_ports[0].port["name"]
            else:
                signal_name = f"sig{signal_counter}"
                signal_counter += 1
            for port in group_ports:
                signal_names[port] = signal_name
    
    top_level_signal_names = set(p.port["name"] for p in top_level_ports)
    internal_signals = set(signal_names.values()) - top_level_signal_names
    
    all_ports = set(port for block in blocks for port in block.port_symbols)
    connected_ports = set(signal_names.keys())
    unconnected_ports = all_ports - connected_ports
    
    with open(filepath, "w") as f:
        f.write("library ieee;\n")
        f.write("use ieee.std_logic_1164.all;\n")
        f.write("use ieee.numeric_std.all;\n\n")
        
        f.write("entity TopLevelAdapter is\n")
        f.write("port(\n")
        for i, port in enumerate(top_level_ports):
            line = f"    {port.port['name']} : {port.port['dir']} {port.port['type']}"
            if i < len(top_level_ports) - 1:
                line += ";"
            f.write(line + "\n")
        f.write(");\nend TopLevelAdapter;\n\n")
        
        f.write("architecture rtl of TopLevelAdapter is\n")
        
        if internal_signals:
            f.write("    -- Internal Signals\n")
            for sig in internal_signals:
                port = next(p for p, s in signal_names.items() if s == sig)
                f.write(f"    signal {sig} : {port.port['type']};\n")
            f.write("\n")
        
        component_ports = defaultdict(list)
        for block in blocks:
            if block.conduit:
                continue
            component_ports[block.name].extend([p.port for p in block.port_symbols])
        
        for comp_name, ports in component_ports.items():
            f.write(f"    component {comp_name} is\n")
            f.write("    port(\n")
            for i, port in enumerate(ports):
                line = f"        {port['name']} : {port['dir']} {port['type']}"
                if i < len(ports) - 1:
                    line += ";"
                f.write(line + "\n")
            f.write("    );\n")
            f.write(f"    end component;\n\n")
        
        adapter_ports = defaultdict(list)
        for block in blocks:
            if isinstance(block, AdapterBlock):
                adapter_ports[block.name].extend([p.port for p in block.port_symbols])
        
        for adapter_name, ports in adapter_ports.items():
            f.write(f"    component {adapter_name} is\n")
            f.write("    port(\n")
            for i, port in enumerate(ports):
                line = f"        {port['name']} : {port['dir']} {port['type']}"
                if i < len(ports) - 1:
                    line += ";"
                f.write(line + "\n")
            f.write("    );\n")
            f.write(f"    end component;\n\n")
        
        f.write("begin\n")
        
        adapter_instances = []
        for block in blocks:
            if isinstance(block, AdapterBlock):
                adapter_instances.append(block)
        
        for adapter in adapter_instances:
            instance_name = f"{adapter.name}_inst"
            f.write(f"    {instance_name} : {adapter.name} port map(\n")
            port_map_lines = []
            for port_symbol in adapter.port_symbols:
                port_name = port_symbol.port["name"]
                if port_symbol in signal_names:
                    signal = signal_names.get(port_symbol, port_name)
                    port_map_lines.append(f"        {port_name} => {signal}")
                else:
                    if port_symbol.port["dir"] in ["in", "inout"]:
                        default_val = get_default_assignment(port_symbol.port["type"])
                        port_map_lines.append(f"        {port_name} => {default_val}")
                    else:
                        port_map_lines.append(f"        {port_name} => open")
            f.write(",\n".join(port_map_lines))
            f.write("\n    );\n\n")
        
        instance_counts = defaultdict(int)
        for block in blocks:
            if block.conduit:
                continue
            if isinstance(block, AdapterBlock):
                continue
            if block.name not in component_ports:
                continue
            instance_counts[block.name] += 1
            idx = instance_counts[block.name] - 1
            instance_name = f"{block.name}_inst{idx}" if instance_counts[block.name] > 1 else f"{block.name}_inst"
            f.write(f"    {instance_name} : {block.name} port map(\n")
            port_map_lines = []
            for port_symbol in block.port_symbols:
                port_name = port_symbol.port["name"]
                if port_symbol in signal_names:
                    signal = signal_names.get(port_symbol, port_symbol.port["name"])
                    port_map_lines.append(f"        {port_name} => {signal}")
                else:
                    if port_symbol.port["dir"] in ["in", "inout"]:
                        default_val = get_default_assignment(port_symbol.port["type"])
                        port_map_lines.append(f"        {port_name} => {default_val}")
                    else:
                        port_map_lines.append(f"        {port_name} => open")
            f.write(",\n".join(port_map_lines))
            f.write("\n    );\n\n")
        
        f.write("end rtl;\n")

def get_default_assignment(vtype):
    vtype = vtype.lower()
    if "std_logic_vector" in vtype:
        return "(others => '0')"
    elif "std_logic" in vtype:
        return "'0'"
    elif "integer" in vtype:
        return "0"
    elif "signed" in vtype or "unsigned" in vtype:
        return "(others => '0')"
    else:
        return "'0'"