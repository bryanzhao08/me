import json
import struct

def parse_glb(file_path):
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        
        chunk0_len = struct.unpack('<I', f.read(4))[0]
        chunk0_type = f.read(4)
        
        json_data = f.read(chunk0_len).decode('utf-8')
        gltf = json.loads(json_data)
        
        print("Meshes:", len(gltf.get('meshes', [])))
        print("Nodes:", len(gltf.get('nodes', [])))
        
        # print first few nodes to see their structure
        print("First 5 nodes:", gltf.get('nodes', [])[:5])

parse_glb('assets/models/hs-01-opt.glb')
