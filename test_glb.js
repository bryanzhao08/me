const fs = require('fs');
const { NodeIO } = require('@gltf-transform/core');
const { KHRONOS_EXTENSIONS } = require('@gltf-transform/extensions');

const io = new NodeIO().registerExtensions(KHRONOS_EXTENSIONS);
const doc = io.read('assets/models/hs-01-opt.glb');

const root = doc.getRoot();
const nodes = root.listNodes();

let out = [];
for (const node of nodes) {
    const mesh = node.getMesh();
    if (mesh) {
        const t = node.getTranslation();
        out.push({name: node.getName() || mesh.getName(), x: t[0], y: t[1], z: t[2]});
    }
}
console.log("Total nodes with meshes:", out.length);
// Print some that are far from origin
out.sort((a,b) => (b.x*b.x + b.y*b.y + b.z*b.z) - (a.x*a.x + a.y*a.y + a.z*a.z));
console.log(out.slice(0, 20));
