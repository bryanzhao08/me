import json
import struct

with open("assets/models/hs-world-opt.glb", 'rb') as f:
    data = f.read()

json_chunk_len, json_chunk_type = struct.unpack('<II', data[12:20])
gltf = json.loads(data[20:20+json_chunk_len].decode('utf-8'))

nodes = gltf.get('nodes', [])
translations = []
for i, node in enumerate(nodes):
    t = node.get('translation', [0,0,0])
    if 'mesh' in node:
        translations.append((i, node.get('name', 'unnamed'), t))

if not translations:
    print("No meshes found")
    exit()

xs = sorted([t[2][0] for t in translations])
ys = sorted([t[2][1] for t in translations])
zs = sorted([t[2][2] for t in translations])
mid = len(xs) // 2
median = [xs[mid], ys[mid], zs[mid]]

print(f"Median: {median}")

for i, name, t in translations:
    dx = t[0] - median[0]
    dy = t[1] - median[1]
    dz = t[2] - median[2]
    dist = (dx**2 + dy**2 + dz**2)**0.5
    if dist > 0.8:
        print(f"OUTLIER: Node {i}: {name} dist={dist:.2f} t={t}")
