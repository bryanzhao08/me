import json
import struct
import sys

def remove_mesh_from_node(in_file, out_file):
    with open(in_file, 'rb') as f:
        data = f.read()

    magic, version, length = struct.unpack('<III', data[:12])
    json_chunk_len, json_chunk_type = struct.unpack('<II', data[12:20])
    json_data = data[20:20+json_chunk_len]
    gltf = json.loads(json_data.decode('utf-8'))

    removed = False
    targets = ['Distance Sensor', 'Optical Sensor', 'Rotation Sensor', 'Inertial Sensor', 'Robot Radio']
    for node in gltf.get('nodes', []):
        if 'name' in node and any(t in node['name'] for t in targets):
            if 'mesh' in node:
                del node['mesh']
                removed = True
                print(f"Removed mesh from node: {node['name']}")

    if not removed:
        print("No target nodes found.")
        return

    new_json_data = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    padding = (4 - (len(new_json_data) % 4)) % 4
    new_json_data += b' ' * padding
    new_json_chunk_len = len(new_json_data)
    
    rest_of_file = data[20+json_chunk_len:]
    new_total_length = 12 + 8 + new_json_chunk_len + len(rest_of_file)
    
    with open(out_file, 'wb') as f:
        f.write(struct.pack('<III', magic, version, new_total_length))
        f.write(struct.pack('<II', new_json_chunk_len, json_chunk_type))
        f.write(new_json_data)
        f.write(rest_of_file)
        
    print(f"Done! New file size: {new_total_length}")

remove_mesh_from_node("assets/models/hs-world-opt.glb", "assets/models/hs-world-nomotor.glb")
remove_mesh_from_node("assets/models/pb-04-optold.glb", "assets/models/pb-04-nomotor.glb")
