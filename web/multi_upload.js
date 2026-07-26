import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "FlexibleMultiImageUploader.Extension",
    async nodeCreated(node) {
        if (node.comfyClass === "FlexibleMultiImageUploader") {
            // Adds an interactive "+ Add Image Slot" button directly on the node
            node.addWidget("button", "➕ Add Image Slot", null, () => {
                let maxIndex = 0;

                if (node.inputs) {
                    for (const input of node.inputs) {
                        const match = input.name?.match(/^image_(\d+)$/);
                        if (match) {
                            const idx = parseInt(match[1]);
                            if (idx > maxIndex) maxIndex = idx;
                        }
                    }
                }

                if (node.widgets) {
                    for (const widget of node.widgets) {
                        const match = widget.name?.match(/^image_(\d+)$/);
                        if (match) {
                            const idx = parseInt(match[1]);
                            if (idx > maxIndex) maxIndex = idx;
                        }
                    }
                }

                const nextIndex = maxIndex + 1;
                const inputName = `image_${nextIndex}`;

                // Add dynamic input slot
                node.addInput(inputName, "IMAGE");
                node.size[1] += 26;
                app.graph.setDirtyCanvas(true, true);
            });
        }
    }
});