import json
import struct

def remove_outliers(file_path, out_path):
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        
        chunk0_len = struct.unpack('<I', f.read(4))[0]
        chunk0_type = f.read(4)
        
        json_data = f.read(chunk0_len).decode('utf-8')
        
        # Read the rest of the file (binary chunk)
        rest = f.read()
        
    gltf = json.loads(json_data)
    
    nodes = gltf.get('nodes', [])
    outlier_indices = set()
    
    # Onshape exports often have translation in 'translation'
    # Z is usually up.
    for i, node in enumerate(nodes):
        if 'translation' in node:
            t = node['translation']
            # Calculate distance
            dist = (t[0]**2 + t[1]**2 + t[2]**2)**0.5
            # If the node is more than 2 meters away from origin, it's an outlier
            # Alternatively, if Z is way too low
            if dist > 1.5 or t[2] < -1.0 or t[1] < -1.0:
                print(f"Found outlier node {i}: {node.get('name', 'unnamed')} at {t}")
                outlier_indices.add(i)
                
    if not outlier_indices:
        print("No outlier nodes found by translation. It might be grouped or have a matrix transform.")
        # Check matrix transforms
        for i, node in enumerate(nodes):
            if 'matrix' in node:
                m = node['matrix']
                # m[12], m[13], m[14] are translation X, Y, Z
                tx, ty, tz = m[12], m[13], m[14]
                dist = (tx**2 + ty**2 + tz**2)**0.5
                if dist > 1.5 or tz < -1.0 or ty < -1.0:
                    print(f"Found outlier matrix node {i}: {node.get('name', 'unnamed')} at {tx}, {ty}, {tz}")
                    outlier_indices.add(i)
    
    # Remove from scenes
    removed = 0
    for scene in gltf.get('scenes', []):
        if 'nodes' in scene:
            old_len = len(scene['nodes'])
            scene['nodes'] = [n for n in scene['nodes'] if n not in outlier_indices]
            removed += (old_len - len(scene['nodes']))
            
    print(f"Removed {removed} nodes from scene root.")
    
    # Also recursively remove from children arrays
    for node in nodes:
        if 'children' in node:
            old_len = len(node['children'])
            node['children'] = [c for c in node['children'] if c not in outlier_indices]
            if len(node['children']) == 0:
                del node['children']
                
    # Write back
    new_json_data = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    # Pad with spaces to multiple of 4
    padding = (4 - (len(new_json_data) % 4)) % 4
    new_json_data += b' ' * padding
    
    new_chunk0_len = len(new_json_data)
    new_length = 12 + 8 + new_chunk0_len + len(rest)
    
    with open(out_path, 'wb') as f:
        f.write(magic)
        f.write(struct.pack('<I', version))
        f.write(struct.pack('<I', new_length))
        
        f.write(struct.pack('<I', new_chunk0_len))
        f.write(chunk0_type)
        f.write(new_json_data)
        f.write(rest)
        
    print("Saved to", out_path)

remove_outliers('assets/models/hs-world.glb', 'assets/models/hs-world-clean.glb')
