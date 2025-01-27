# generator.py
import os
from collections import defaultdict
from gui_components import AdapterBlock, EntityBlock
import re

def generate_top_level(canvas):
    adapters_dir = "Adapters"
    os.makedirs(adapters_dir, exist_ok=True)
    filepath = os.path.join(adapters_dir, "TopLevelAdapter.vhd")
    
    blocks = canvas.data["blocks"]
    connections = canvas.data["connections"]
    
    conduit_blocks = [block for block in blocks if block.conduit]
    
    conduit_ports = []
    for block in blocks:
        if isinstance(block, EntityBlock) or isinstance(block, AdapterBlock):
            for port in block.port_symbols:
                if hasattr(port, 'is_conduit') and port.is_conduit:
                    conduit_ports.append(port)
    
    top_level_input_ports = [p for block in conduit_blocks for p in block.port_symbols if p.port["dir"] in ["in", "inout"]]
    top_level_output_ports = [p for block in conduit_blocks for p in block.port_symbols if p.port["dir"] in ["out", "inout"]]
    
    top_level_input_ports += [p for p in conduit_ports if p.port["dir"] in ["in", "inout"]]
    top_level_output_ports += [p for p in conduit_ports if p.port["dir"] in ["out", "inout"]]
    
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
        input_conduits = [p for p in group_ports if p in top_level_input_ports]
        output_conduits = [p for p in group_ports if p in top_level_output_ports]
        if input_conduits and output_conduits:
            signal_name = f"sig{signal_counter}"
            signal_counter +=1
            for p in group_ports:
                signal_names[p] = signal_name
        elif input_conduits:
            signal_name = input_conduits[0].port["name"]
            for p in group_ports:
                signal_names[p] = signal_name
        elif output_conduits:
            signal_name = output_conduits[0].port["name"]
            for p in group_ports:
                signal_names[p] = signal_name
        else:
            signal_name = f"sig{signal_counter}"
            signal_counter +=1
            for p in group_ports:
                signal_names[p] = signal_name
    
    top_level_signal_names = set(p.port["name"] for block in conduit_blocks for p in block.port_symbols)
    top_level_signal_names.update(p.port["name"] for p in conduit_ports)
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
        all_conduit_ports = [p for block in conduit_blocks for p in block.port_symbols] + conduit_ports
        for i, port in enumerate(all_conduit_ports):
            if isinstance(port.block, EntityBlock) and port.block.conduit:
                original_dir = flip_direction(port.port["dir"])
            else:
                original_dir = port.port["dir"]
            
            line = f"    {port.port['name']} : {original_dir} {port.port['type']}"
            if i < len(all_conduit_ports) -1:
                line += ";"
            f.write(line + "\n")
        f.write(");\nend TopLevelAdapter;\n\n")
        
        f.write("architecture rtl of TopLevelAdapter is\n")
        
        if internal_signals:
            f.write("    -- Internal Signals\n")
            for sig in internal_signals:
                associated_ports = [p for p, s in signal_names.items() if s == sig]
                if associated_ports:
                    port = associated_ports[0].port
                    f.write(f"    signal {sig} : {port['type']};\n")
            f.write("\n")
        
        component_ports = defaultdict(list)
        component_generics = defaultdict(list)
        for block in blocks:
            if block.conduit:
                continue
            if isinstance(block, EntityBlock):
                component_ports[block.name].extend([p.port for p in block.port_symbols])
                if block.generics:
                    component_generics[block.name].extend(block.generics)
            elif isinstance(block, AdapterBlock):
                component_ports[block.name].extend([p.port for p in block.port_symbols])
        
        for comp_name, ports in component_ports.items():
            f.write(f"    component {comp_name} is\n")
            if component_generics[comp_name]:
                f.write("    generic(\n")
                for i, gen in enumerate(component_generics[comp_name]):
                    line = f"        {gen['name']} : {gen['type']}"
                    if gen.get("default"):
                        line += f" := {gen['default']}"
                    if i < len(component_generics[comp_name]) -1:
                        line += ";"
                    f.write(line + "\n")
                f.write("    );\n")
            f.write("    port(\n")
            for i, port in enumerate(ports):
                line = f"        {port['name']} : {port['dir']} {port['type']}"
                if i < len(ports) -1:
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
            if isinstance(block, EntityBlock):
                instance_counts[block.name] +=1
                idx = instance_counts[block.name] -1
                instance_name = f"{block.name}_inst{idx}" if instance_counts[block.name] >1 else f"{block.name}_inst"
                if block.generics:
                    f.write(f"    {instance_name} : {block.name} generic map(\n")
                    gen_map_lines = []
                    for gen in block.generics:
                        gen_name = gen['name']
                        gen_value = block.generic_values.get(gen_name, gen.get("default"))
                        if isinstance(gen_value, str) and not (gen_value.startswith("'") or gen_value.startswith('"')):
                            gen_value = f'"{gen_value}"'
                        gen_map_lines.append(f"        {gen_name} => {gen_value}")
                    f.write(",\n".join(gen_map_lines))
                    f.write("\n    ) port map(\n")
                else:
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

def flip_direction(direction):
    if direction == "in":
        return "out"
    elif direction == "out":
        return "in"
    else:
        return direction

def get_default_assignment(vtype):
    vtype = vtype.lower()
    if "std_logic_vector" in vtype:
        match = re.search(r'\((\d+):0\)', vtype)
        if match:
            width = int(match.group(1)) + 1
            return f"(others => '0')" if width > 1 else "'0'"
        return "(others => '0')"
    elif "std_logic" in vtype:
        return "'0'"
    elif "integer" in vtype:
        return "0"
    elif "signed" in vtype or "unsigned" in vtype:
        return "(others => '0')"
    else:
        return "'0'"
