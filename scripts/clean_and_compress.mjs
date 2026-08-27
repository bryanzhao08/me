#!/usr/bin/env node
/**
 * clean_and_compress.mjs — Uses gltf-transform to:
 * 1. Prune unreferenced data (orphaned meshes, accessors, buffers)
 * 2. Detect and remove detached/floating mesh primitives by world-space position
 * 3. Remove sensor nodes by name
 * 4. Dedup duplicate materials/accessors
 * 5. Apply Draco compression (quantize only, no vertex deletion)
 * 
 * Usage: node scripts/clean_and_compress.mjs
 */

import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, prune, draco } from '@gltf-transform/functions';
import draco3d from 'draco3dgltf';

const SENSOR_NAMES = ['Distance Sensor', 'Optical Sensor', 'Rotation Sensor', 'Inertial Sensor', 'Robot Radio'];

/**
 * Get the world-space bounding box center of a mesh primitive's geometry.
 * Walks up the node hierarchy to accumulate transforms.
 */
function getMeshWorldCenter(node) {
  // Get the node's world translation by walking up parents
  let tx = 0, ty = 0, tz = 0;
  let current = node;
  while (current) {
    const t = current.getTranslation();
    tx += t[0]; ty += t[1]; tz += t[2];
    current = current.getParentNode ? current.getParentNode() : null;
  }
  return [tx, ty, tz];
}

/**
 * Get approximate world-space center of a mesh primitive by reading position accessor min/max.
 */
function getPrimitiveCenter(primitive, nodeWorldPos) {
  const posAccessor = primitive.getAttribute('POSITION');
  if (!posAccessor) return null;
  
  const min = posAccessor.getMin(new Array(3));
  const max = posAccessor.getMax(new Array(3));
  
  // Local center of the primitive
  const cx = (min[0] + max[0]) / 2 + nodeWorldPos[0];
  const cy = (min[1] + max[1]) / 2 + nodeWorldPos[1];
  const cz = (min[2] + max[2]) / 2 + nodeWorldPos[2];
  
  return [cx, cy, cz];
}

/**
 * DBSCAN clustering on 3D points.
 */
function dbscan(points, eps) {
  const n = points.length;
  const labels = new Array(n).fill(-1);
  let clusterId = 0;

  function dist(a, b) {
    const dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2];
    return Math.sqrt(dx*dx + dy*dy + dz*dz);
  }

  for (let i = 0; i < n; i++) {
    if (labels[i] !== -1) continue;
    
    labels[i] = clusterId;
    const queue = [i];
    
    while (queue.length > 0) {
      const current = queue.shift();
      for (let j = 0; j < n; j++) {
        if (labels[j] !== -1) continue;
        if (dist(points[current], points[j]) <= eps) {
          labels[j] = clusterId;
          queue.push(j);
        }
      }
    }
    clusterId++;
  }

  return labels;
}

/**
 * Remove sensor nodes by name pattern.
 */
function removeSensorNodes(doc) {
  const root = doc.getRoot();
  let removed = 0;
  
  for (const node of root.listNodes()) {
    const name = node.getName();
    if (SENSOR_NAMES.some(s => name.includes(s))) {
      const mesh = node.getMesh();
      if (mesh) {
        node.setMesh(null);
        removed++;
        console.log(`    Removed sensor mesh: ${name}`);
      }
    }
  }
  console.log(`    Total sensor meshes removed: ${removed}`);
  return removed;
}

/**
 * Detect and remove detached/floating parts at the node level using DBSCAN.
 */
function removeDetachedNodes(doc, eps = 0.12) {
  const root = doc.getRoot();
  const meshNodes = [];
  const centers = [];
  
  for (const node of root.listNodes()) {
    if (!node.getMesh()) continue;
    const worldPos = getMeshWorldCenter(node);
    meshNodes.push(node);
    centers.push(worldPos);
  }

  console.log(`    Mesh nodes to cluster: ${meshNodes.length}`);
  if (meshNodes.length <= 1) return 0;

  const labels = dbscan(centers, eps);
  
  // Find largest cluster
  const counts = {};
  labels.forEach(l => { counts[l] = (counts[l] || 0) + 1; });
  const mainCluster = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
  
  console.log(`    Clusters: ${Object.keys(counts).length}`);
  for (const [cid, count] of Object.entries(counts).sort((a, b) => b[1] - a[1])) {
    const marker = cid === mainCluster ? ' ← MAIN' : ' ← REMOVE';
    console.log(`      Cluster ${cid}: ${count} nodes${marker}`);
  }

  let removed = 0;
  for (let i = 0; i < meshNodes.length; i++) {
    if (String(labels[i]) !== mainCluster) {
      console.log(`    Removing detached node: ${meshNodes[i].getName()}`);
      meshNodes[i].dispose();
      removed++;
    }
  }

  return removed;
}

/**
 * Remove detached floating primitives within meshes based on Z-coordinate clustering.
 * This catches the case where individual primitives within a shared mesh are floating.
 */
function removeDetachedPrimitives(doc, zThreshold = 0.10) {
  const root = doc.getRoot();
  let totalRemoved = 0;
  
  for (const node of root.listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    
    const worldPos = getMeshWorldCenter(node);
    const primitives = mesh.listPrimitives();
    if (primitives.length <= 1) continue;
    
    // Compute Z-center for each primitive
    const primData = [];
    for (const prim of primitives) {
      const center = getPrimitiveCenter(prim, worldPos);
      if (center) {
        primData.push({ prim, center, z: center[2] });
      }
    }
    
    if (primData.length <= 1) continue;
    
    // Find median Z
    const zVals = primData.map(p => p.z).sort((a, b) => a - b);
    const medZ = zVals[Math.floor(zVals.length / 2)];
    
    // Remove primitives far from median Z
    const toRemove = primData.filter(p => Math.abs(p.z - medZ) > zThreshold);
    
    if (toRemove.length > 0 && toRemove.length < primData.length * 0.9) {
      // Only remove if it's a minority of primitives (don't remove most of the mesh)
      for (const { prim } of toRemove) {
        mesh.removePrimitive(prim);
        totalRemoved++;
      }
      if (toRemove.length > 5) {
        console.log(`    Node "${node.getName()}": removed ${toRemove.length}/${primData.length} floating prims (medZ=${medZ.toFixed(4)})`);
      }
    }
  }
  
  console.log(`    Total floating primitives removed: ${totalRemoved}`);
  return totalRemoved;
}


async function processModel(io, inputPath, outputPath, options = {}) {
  const { eps = 0.12, removeSensors = true, zThreshold = 0.10 } = options;
  
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Processing: ${inputPath}`);
  console.log(`Output:     ${outputPath}`);
  console.log(`${'='.repeat(60)}`);

  const doc = await io.read(inputPath);
  const root = doc.getRoot();
  
  const nodeCount = root.listNodes().length;
  const meshCount = root.listMeshes().length;
  const totalPrims = root.listMeshes().reduce((s, m) => s + m.listPrimitives().length, 0);
  console.log(`  Nodes: ${nodeCount}, Meshes: ${meshCount}, Primitives: ${totalPrims}`);
  
  // Step 1: Remove sensor meshes
  if (removeSensors) {
    console.log('\n  Step 1: Removing sensor meshes...');
    removeSensorNodes(doc);
  }
  
  // Step 2: Remove detached nodes (DBSCAN)
  console.log(`\n  Step 2: Detecting detached nodes (eps=${eps})...`);
  removeDetachedNodes(doc, eps);
  
  // Step 3: Remove detached primitives within meshes  
  console.log(`\n  Step 3: Detecting floating primitives (zThreshold=${zThreshold})...`);
  removeDetachedPrimitives(doc, zThreshold);
  
  // Step 4: Prune unreferenced data
  console.log('\n  Step 4: Pruning unreferenced data...');
  await doc.transform(prune());
  
  // Step 5: Dedup
  console.log('  Step 5: Deduplicating...');
  await doc.transform(dedup());
  
  // Step 6: Draco compression
  console.log('  Step 6: Applying Draco compression...');
  await doc.transform(
    draco({
      quantizePosition: 14,
      quantizeNormal: 10,
      quantizeTexcoord: 12,
    })
  );
  
  // Write output
  await io.write(outputPath, doc);
  
  // Report
  const { size } = await import('fs').then(fs => fs.statSync(outputPath));
  console.log(`\n  Output size: ${(size / 1024 / 1024).toFixed(1)} MB`);
  
  const finalMeshCount = root.listMeshes().length;
  const finalPrims = root.listMeshes().reduce((s, m) => s + m.listPrimitives().length, 0);
  console.log(`  Final: ${finalMeshCount} meshes, ${finalPrims} primitives`);
}


async function main() {
  console.log('Initializing gltf-transform + Draco...');
  
  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({
      'draco3d.decoder': await draco3d.createDecoderModule(),
      'draco3d.encoder': await draco3d.createEncoderModule(),
    });

  const models = [
    {
      input: 'assets/models/hs-world-opt.glb',
      output: 'assets/models/hs-world-fast.glb',
      eps: 0.12,
      zThreshold: 0.10,
    },
    {
      input: 'assets/models/pb-04-nomotor.glb', 
      output: 'assets/models/pb-04-fast.glb',
      eps: 0.15,
      zThreshold: 0.10,
    },
    {
      input: 'assets/models/ou-opt.glb',
      output: 'assets/models/ou-opt-new.glb',
      eps: 0.15,
      removeSensors: false,
      zThreshold: 0.10,
    },
  ];

  for (const model of models) {
    await processModel(io, model.input, model.output, model);
  }

  // Rename ou-opt-new → ou-opt
  const fs = await import('fs');
  if (fs.existsSync('assets/models/ou-opt-new.glb')) {
    fs.renameSync('assets/models/ou-opt-new.glb', 'assets/models/ou-opt.glb');
    console.log('\n  Renamed ou-opt-new.glb → ou-opt.glb');
  }

  console.log('\n✓ All models processed!');
}

main().catch(err => { console.error(err); process.exit(1); });
