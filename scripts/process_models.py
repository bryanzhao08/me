#!/usr/bin/env python3
"""
process_models.py — Detect & remove detached floating parts from GLB models,
then recompress with Draco (no vertex deletion).

Usage:
    python3 scripts/process_models.py

Pipeline per model:
  1. Parse GLB JSON chunk to get node/mesh structure
  2. Compute world-space bounding-box center for each mesh node
  3. DBSCAN-cluster mesh centers → largest cluster = main robot body
  4. Remove nodes not in main cluster from the scene graph
  5. Write cleaned GLB
  6. Run gltf-transform CLI: dedup → draco (quantize only, no simplify)
"""

import json
import struct
import math
import subprocess
import os
import sys
import shutil
from collections import deque

# ─── GLB I/O ───────────────────────────────────────────────────────────────────

def read_glb(path):
    """Read a GLB file and return (header_info, gltf_json, binary_chunk)."""
    with open(path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]

        chunk0_len = struct.unpack('<I', f.read(4))[0]
        chunk0_type = f.read(4)
        json_bytes = f.read(chunk0_len)

        rest = f.read()  # binary chunk (header + data)

    gltf = json.loads(json_bytes.decode('utf-8'))
    return {
        'magic': magic,
        'version': version,
        'chunk0_type': chunk0_type,
    }, gltf, rest


def write_glb(path, header, gltf, binary_rest):
    """Write a GLB file from components."""
    json_bytes = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    # Pad JSON chunk to 4-byte boundary with spaces (per spec)
    padding = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b' ' * padding

    total_length = 12 + 8 + len(json_bytes) + len(binary_rest)

    with open(path, 'wb') as f:
        f.write(header['magic'])
        f.write(struct.pack('<I', header['version']))
        f.write(struct.pack('<I', total_length))
        f.write(struct.pack('<I', len(json_bytes)))
        f.write(header['chunk0_type'])
        f.write(json_bytes)
        f.write(binary_rest)


# ─── World transform computation ──────────────────────────────────────────────

def mat4_identity():
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]


def mat4_multiply(a, b):
    """Multiply two 4x4 matrices stored as flat 16-element lists (column-major, glTF convention)."""
    result = [0.0] * 16
    for col in range(4):
        for row in range(4):
            s = 0.0
            for k in range(4):
                s += a[row + k * 4] * b[k + col * 4]
            result[row + col * 4] = s
    return result


def node_local_matrix(node):
    """Get the local transform matrix for a node."""
    if 'matrix' in node:
        return list(node['matrix'])

    m = mat4_identity()

    # TRS: T * R * S
    s = node.get('scale', [1, 1, 1])
    # Apply scale
    m[0] = s[0]; m[5] = s[1]; m[10] = s[2]

    # Apply rotation (quaternion)
    if 'rotation' in node:
        qx, qy, qz, qw = node['rotation']
        # Quaternion to rotation matrix
        rm = mat4_identity()
        rm[0] = 1 - 2*(qy*qy + qz*qz)
        rm[1] = 2*(qx*qy + qz*qw)
        rm[2] = 2*(qx*qz - qy*qw)
        rm[4] = 2*(qx*qy - qz*qw)
        rm[5] = 1 - 2*(qx*qx + qz*qz)
        rm[6] = 2*(qy*qz + qx*qw)
        rm[8] = 2*(qx*qz + qy*qw)
        rm[9] = 2*(qy*qz - qx*qw)
        rm[10] = 1 - 2*(qx*qx + qy*qy)
        m = mat4_multiply(rm, m)

    # Apply translation
    t = node.get('translation', [0, 0, 0])
    tm = mat4_identity()
    tm[12] = t[0]; tm[13] = t[1]; tm[14] = t[2]
    m = mat4_multiply(tm, m)

    return m


def compute_world_matrices(nodes):
    """Compute world transform for each node index. Returns dict {node_idx: mat4}."""
    world = {}
    # Build parent map
    parent_map = {}
    for i, node in enumerate(nodes):
        for child_idx in node.get('children', []):
            parent_map[child_idx] = i

    def get_world(idx):
        if idx in world:
            return world[idx]
        local = node_local_matrix(nodes[idx])
        if idx in parent_map:
            parent_world = get_world(parent_map[idx])
            world[idx] = mat4_multiply(parent_world, local)
        else:
            world[idx] = local
        return world[idx]

    for i in range(len(nodes)):
        get_world(i)

    return world


def transform_point(mat, point):
    """Transform a 3D point by a 4x4 column-major matrix."""
    x, y, z = point
    return [
        mat[0]*x + mat[4]*y + mat[8]*z + mat[12],
        mat[1]*x + mat[5]*y + mat[9]*z + mat[13],
        mat[2]*x + mat[6]*y + mat[10]*z + mat[14],
    ]


# ─── DBSCAN-style clustering ──────────────────────────────────────────────────

def dbscan_cluster(points, eps, min_samples=1):
    """
    Simple DBSCAN clustering on 3D points.
    Returns list of cluster labels (-1 = noise).
    """
    n = len(points)
    labels = [-1] * n
    cluster_id = 0

    def neighbors(idx):
        p = points[idx]
        result = []
        for j in range(n):
            if j == idx:
                continue
            dx = points[j][0] - p[0]
            dy = points[j][1] - p[1]
            dz = points[j][2] - p[2]
            if math.sqrt(dx*dx + dy*dy + dz*dz) <= eps:
                result.append(j)
        return result

    for i in range(n):
        if labels[i] != -1:
            continue
        nbrs = neighbors(i)
        if len(nbrs) < min_samples - 1:  # -1 because point itself counts
            # Could be noise, but with min_samples=1 everything gets a cluster
            pass

        # Start a new cluster
        labels[i] = cluster_id
        queue = deque(nbrs)
        while queue:
            j = queue.popleft()
            if labels[j] != -1:
                continue
            labels[j] = cluster_id
            j_nbrs = neighbors(j)
            queue.extend(j_nbrs)

        cluster_id += 1

    return labels


# ─── Detached-part detection ──────────────────────────────────────────────────

def find_mesh_node_centers(gltf):
    """
    Find world-space center positions for all nodes that have a mesh.
    Returns list of (node_index, [x, y, z]).
    """
    nodes = gltf.get('nodes', [])
    world_matrices = compute_world_matrices(nodes)

    mesh_centers = []
    for i, node in enumerate(nodes):
        if 'mesh' not in node:
            continue
        # Use the node's world-space origin (translation part of world matrix)
        wm = world_matrices[i]
        center = [wm[12], wm[13], wm[14]]
        mesh_centers.append((i, center))

    return mesh_centers


def detect_detached_parts(gltf, eps=0.15):
    """
    Detect detached floating parts using DBSCAN clustering.
    Returns set of node indices to remove (everything not in the largest cluster).
    """
    mesh_centers = find_mesh_node_centers(gltf)

    if len(mesh_centers) <= 1:
        print("    Only 0-1 mesh nodes found, nothing to cluster.")
        return set()

    points = [c for _, c in mesh_centers]
    node_indices = [idx for idx, _ in mesh_centers]

    labels = dbscan_cluster(points, eps=eps)

    # Find the largest cluster
    cluster_counts = {}
    for label in labels:
        cluster_counts[label] = cluster_counts.get(label, 0) + 1

    largest_cluster = max(cluster_counts, key=cluster_counts.get)

    to_remove = set()
    for i, label in enumerate(labels):
        if label != largest_cluster:
            to_remove.add(node_indices[i])

    # Report
    print(f"    Clusters found: {len(cluster_counts)}")
    for cid, count in sorted(cluster_counts.items(), key=lambda x: -x[1]):
        marker = " <-- MAIN" if cid == largest_cluster else " <-- REMOVE"
        print(f"      Cluster {cid}: {count} mesh nodes{marker}")

    return to_remove


# ─── Node removal from scene graph ────────────────────────────────────────────

def collect_descendants(nodes, node_idx):
    """Collect all descendant node indices (including the node itself)."""
    result = {node_idx}
    for child_idx in nodes[node_idx].get('children', []):
        result |= collect_descendants(nodes, child_idx)
    return result


def remove_nodes_from_scene(gltf, remove_indices):
    """Remove nodes from scene roots and parent children arrays."""
    nodes = gltf.get('nodes', [])

    # Also collect all descendants of removed nodes
    all_remove = set()
    for idx in remove_indices:
        all_remove |= collect_descendants(nodes, idx)

    removed_from_scenes = 0
    for scene in gltf.get('scenes', []):
        if 'nodes' in scene:
            old_len = len(scene['nodes'])
            scene['nodes'] = [n for n in scene['nodes'] if n not in all_remove]
            removed_from_scenes += old_len - len(scene['nodes'])

    removed_from_children = 0
    for node in nodes:
        if 'children' in node:
            old_len = len(node['children'])
            node['children'] = [c for c in node['children'] if c not in all_remove]
            removed_from_children += old_len - len(node['children'])
            if len(node['children']) == 0:
                del node['children']

    # Remove mesh references from removed nodes (so binary data can be cleaned)
    meshes_removed = 0
    for idx in all_remove:
        if idx < len(nodes) and 'mesh' in nodes[idx]:
            del nodes[idx]['mesh']
            meshes_removed += 1

    print(f"    Removed {removed_from_scenes} from scene roots, {removed_from_children} from children")
    print(f"    Detached {meshes_removed} mesh references from {len(all_remove)} total nodes")

    return len(all_remove)


# ─── Also remove sensor/motor meshes by name ─────────────────────────────────

SENSOR_NAMES = ['Distance Sensor', 'Optical Sensor', 'Rotation Sensor', 'Inertial Sensor', 'Robot Radio']

def remove_sensor_meshes(gltf):
    """Remove mesh references from sensor nodes (these are internal CAD artifacts)."""
    nodes = gltf.get('nodes', [])
    removed = 0
    for node in nodes:
        name = node.get('name', '')
        if any(s in name for s in SENSOR_NAMES):
            if 'mesh' in node:
                del node['mesh']
                removed += 1
                print(f"    Removed sensor mesh: {name}")
    return removed


# ─── gltf-transform recompression ─────────────────────────────────────────────

def run_gltf_transform(input_path, output_path):
    """Run gltf-transform CLI pipeline: dedup → draco compression."""
    # Use a temp intermediate file
    temp_path = output_path + '.tmp.glb'

    steps = [
        # Step 1: Dedup — merge duplicate accessors and materials
        ['npx', '-y', '@gltf-transform/cli', 'dedup', input_path, temp_path],
        # Step 2: Draco compression — quantize positions (14 bits) and normals (10 bits)
        # This does NOT delete vertices — it only quantizes float precision for compression
        ['npx', '-y', '@gltf-transform/cli', 'draco', temp_path, output_path,
         '--quantize-position', '14',
         '--quantize-normal', '10',
         '--quantize-texcoord', '12',
        ],
    ]

    for step in steps:
        print(f"    Running: {' '.join(step[-4:])}")
        result = subprocess.run(step, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr}")
            # If draco fails, try without quantize args
            if 'draco' in step:
                print("    Retrying draco without explicit quantization...")
                fallback = ['npx', '-y', '@gltf-transform/cli', 'draco', temp_path, output_path]
                result = subprocess.run(fallback, capture_output=True, text=True, cwd=os.getcwd())
                if result.returncode != 0:
                    print(f"    FALLBACK ALSO FAILED: {result.stderr}")
                    # Just copy the deduped version
                    shutil.copy2(temp_path, output_path)
        if result.stdout:
            print(f"    {result.stdout.strip()}")

    # Clean up temp
    if os.path.exists(temp_path):
        os.remove(temp_path)


# ─── Main pipeline ────────────────────────────────────────────────────────────

def process_model(input_path, output_path, eps=0.15, remove_sensors=True):
    """Full pipeline: detect detached parts → remove → recompress."""
    print(f"\n{'='*60}")
    print(f"Processing: {input_path}")
    print(f"Output:     {output_path}")
    print(f"{'='*60}")

    input_size = os.path.getsize(input_path)
    print(f"  Input size: {input_size / 1024 / 1024:.1f} MB")

    # Step 1: Read GLB
    header, gltf, binary = read_glb(input_path)
    nodes = gltf.get('nodes', [])
    meshes = gltf.get('meshes', [])
    print(f"  Nodes: {len(nodes)}, Meshes: {len(meshes)}")

    # Step 2: Remove sensor meshes
    if remove_sensors:
        print("\n  Removing sensor meshes...")
        remove_sensor_meshes(gltf)

    # Step 3: Detect detached parts
    print(f"\n  Detecting detached parts (eps={eps})...")
    detached = detect_detached_parts(gltf, eps=eps)

    if detached:
        print(f"\n  Removing {len(detached)} detached mesh nodes...")
        remove_nodes_from_scene(gltf, detached)
    else:
        print("  No detached parts found!")

    # Step 4: Write cleaned GLB (intermediate)
    cleaned_path = output_path + '.cleaned.glb'
    write_glb(cleaned_path, header, gltf, binary)
    cleaned_size = os.path.getsize(cleaned_path)
    print(f"\n  Cleaned size: {cleaned_size / 1024 / 1024:.1f} MB")

    # Step 5: Recompress with gltf-transform
    print("\n  Recompressing with gltf-transform...")
    run_gltf_transform(cleaned_path, output_path)

    # Clean up intermediate
    if os.path.exists(cleaned_path):
        os.remove(cleaned_path)

    if os.path.exists(output_path):
        output_size = os.path.getsize(output_path)
        print(f"\n  Final size: {output_size / 1024 / 1024:.1f} MB")
        print(f"  Reduction: {(1 - output_size / input_size) * 100:.1f}%")
    else:
        print("\n  WARNING: Output file was not created!")


def verify_model(path):
    """Run gltf-transform inspect on the output for verification."""
    print(f"\n  Verifying {path}...")
    result = subprocess.run(
        ['npx', '-y', '@gltf-transform/cli', 'inspect', path],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    if result.returncode == 0:
        # Extract just the SCENES section for vertex counts
        lines = result.stdout.split('\n')
        in_scenes = False
        for line in lines:
            if 'SCENES' in line:
                in_scenes = True
            if in_scenes:
                print(f"    {line}")
            if in_scenes and line.strip() == '':
                break
    else:
        print(f"    Inspect failed: {result.stderr}")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    models = [
        {
            'input': 'assets/models/hs-world-opt.glb',
            'output': 'assets/models/hs-world-fast.glb',
            'eps': 0.12,  # tighter for this model — many parts close together
        },
        {
            'input': 'assets/models/pb-04-nomotor.glb',
            'output': 'assets/models/pb-04-fast.glb',
            'eps': 0.15,
        },
        {
            'input': 'assets/models/ou-opt.glb',
            'output': 'assets/models/ou-opt-new.glb',  # don't overwrite source
            'eps': 0.15,
            'remove_sensors': False,  # already clean
        },
    ]

    for model in models:
        process_model(
            model['input'],
            model['output'],
            eps=model.get('eps', 0.15),
            remove_sensors=model.get('remove_sensors', True),
        )

    print("\n" + "="*60)
    print("All models processed. Verifying...")
    print("="*60)

    for model in models:
        verify_model(model['output'])

    # Rename ou-opt-new to ou-opt
    if os.path.exists('assets/models/ou-opt-new.glb'):
        os.replace('assets/models/ou-opt-new.glb', 'assets/models/ou-opt.glb')
        print("\n  Renamed ou-opt-new.glb -> ou-opt.glb")

    print("\nDone!")
