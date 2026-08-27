import json
import struct
import math

with open("assets/models/hs-world-nomotor.glb", 'rb') as f:
    data = f.read()

json_chunk_len, json_chunk_type = struct.unpack('<II', data[12:20])
gltf = json.loads(data[20:20+json_chunk_len].decode('utf-8'))

for i, node in enumerate(gltf.get('nodes', [])):
    t = node.get('translation', [0,0,0])
    dist = math.sqrt(t[0]**2 + t[1]**2 + t[2]**2)
    if dist > 0.1:
        print(f"Node {i}: {node.get('name', 'unnamed')} translation={t}")
