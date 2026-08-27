import { Document, NodeIO } from '@gltf-transform/core';
import { bounds } from '@gltf-transform/functions';
import fs from 'fs';

async function main() {
    const io = new NodeIO();
    const doc = await io.read('assets/models/hs-world.glb');
    const root = doc.getRoot();
    const nodes = root.listNodes();
    
    console.log(`Total nodes: ${nodes.length}`);
    
    // We need to calculate bounds for each node
    // But @gltf-transform/functions bounds() works on scenes or nodes
    let removedCount = 0;
    
    // To avoid complex world transforms, let's just find nodes with a huge translation
    for (const node of nodes) {
        const t = node.getTranslation();
        // Calculate distance from origin (assuming robot is near origin)
        const dist = Math.sqrt(t[0]*t[0] + t[1]*t[1] + t[2]*t[2]);
        if (dist > 1.5) {
            console.log(`Found outlier node: ${node.getName()} at distance ${dist}`);
            node.dispose();
            removedCount++;
        }
    }
    
    if (removedCount > 0) {
        console.log(`Removed ${removedCount} nodes. Saving to hs-world-clean.glb...`);
        await io.write('assets/models/hs-world-clean.glb', doc);
        console.log("Done.");
    } else {
        console.log("No outliers found by translation. They might be baked into mesh geometry.");
    }
}

main().catch(console.error);
