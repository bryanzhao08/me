import json, struct

def parse_glb(file_path):
    with open(file_path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        chunk0_len = struct.unpack('<I', f.read(4))[0]
        chunk0_type = f.read(4)
        json_data = f.read(chunk0_len).decode('utf-8')
        gltf = json.loads(json_data)
        
        nodes = gltf.get('nodes', [])
        for i, n in enumerate(nodes):
            if 'translation' in n:
                t = n['translation']
                if abs(t[0]) > 1 or abs(t[1]) > 1 or abs(t[2]) > 1:
                    print(f"Node {i} ({n.get('name')}): {t}")

parse_glb('assets/models/hs-01-opt.glb')
