import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "FlexibleMultiImageUploader.Extension",
    async nodeCreated(node) {
        if (node.comfyClass === "FlexibleMultiImageUploader") {
            node.uploadedImages = []; // Array of { name, imgElement }

            // Hide raw JSON text widget from UI
            const jsonWidget = node.widgets?.find(w => w.name === "image_list_json");
            if (jsonWidget) {
                jsonWidget.type = "hidden";
                jsonWidget.computeSize = () => [0, -4];
            }

            const updateJsonWidget = () => {
                if (jsonWidget) {
                    const fileNames = node.uploadedImages.map(item => item.name);
                    jsonWidget.value = JSON.stringify(fileNames);
                }
            };

            const updateNodeSize = () => {
                const count = node.uploadedImages.length;
                const cols = 2;
                const rows = Math.ceil(count / cols) || 1;
                const cellHeight = 90;
                const baseHeight = 130;
                node.size[0] = Math.max(node.size[0], 240);
                node.size[1] = baseHeight + (rows * cellHeight);
                app.graph.setDirtyCanvas(true, true);
            };

            const uploadFile = async (file) => {
                const body = new FormData();
                body.append("image", file);
                body.append("overwrite", "true");

                try {
                    const resp = await api.fetchApi("/upload/image", {
                        method: "POST",
                        body,
                    });

                    if (resp.status === 200) {
                        const data = await resp.json();
                        const filename = data.name;
                        const subfolder = data.subfolder || "";
                        const fullPath = subfolder ? `${subfolder}/${filename}` : filename;

                        const img = new Image();
                        img.src = api.apiURL(`/view?filename=${encodeURIComponent(filename)}&subfolder=${encodeURIComponent(subfolder)}&type=${data.type || "input"}`);
                        
                        img.onload = () => {
                            app.graph.setDirtyCanvas(true, true);
                        };

                        node.uploadedImages.push({ name: fullPath, imgElement: img });
                        updateJsonWidget();
                        updateNodeSize();
                    }
                } catch (error) {
                    console.error("Upload failed:", error);
                }
            };

            // Single Upload Button (Appends to grid each time clicked)
            node.addWidget("button", "📤 Upload Image", null, () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "image/*";
                input.multiple = true;
                input.onchange = async () => {
                    if (input.files && input.files.length > 0) {
                        for (const file of input.files) {
                            await uploadFile(file);
                        }
                    }
                };
                input.click();
            });

            // Clear Button to reset the grid
            node.addWidget("button", "🗑️ Clear Grid", null, () => {
                node.uploadedImages = [];
                updateJsonWidget();
                updateNodeSize();
            });

            // Render interactive Grid Preview on Canvas
            const origDrawForeground = node.onDrawForeground;
            node.onDrawForeground = function (ctx) {
                if (origDrawForeground) origDrawForeground.apply(this, arguments);
                if (this.flags.collapsed) return;

                const count = this.uploadedImages ? this.uploadedImages.length : 0;
                if (count === 0) {
                    ctx.fillStyle = "#888";
                    ctx.font = "12px sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText("No images uploaded yet", this.size[0] / 2, this.size[1] - 25);
                    return;
                }

                const padding = 10;
                const startY = 100;
                const cols = 2;
                const gap = 8;
                const gridW = this.size[0] - (padding * 2);
                const cellW = (gridW - gap) / cols;
                const cellH = cellW * 0.75;

                this.uploadedImages.forEach((item, idx) => {
                    const col = idx % cols;
                    const row = Math.floor(idx / cols);

                    const x = padding + col * (cellW + gap);
                    const y = startY + row * (cellH + gap);

                    // Thumbnail container box
                    ctx.fillStyle = "#1a1a1a";
                    ctx.strokeStyle = "#333";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    if (ctx.roundRect) ctx.roundRect(x, y, cellW, cellH, 6);
                    else ctx.rect(x, y, cellW, cellH);
                    ctx.fill();
                    ctx.stroke();

                    // Render image thumbnail inside grid cell
                    if (item.imgElement && item.imgElement.complete && item.imgElement.naturalWidth > 0) {
                        ctx.save();
                        ctx.beginPath();
                        if (ctx.roundRect) ctx.roundRect(x + 2, y + 2, cellW - 4, cellH - 4, 4);
                        else ctx.rect(x + 2, y + 2, cellW - 4, cellH - 4);
                        ctx.clip();
                        ctx.drawImage(item.imgElement, x + 2, y + 2, cellW - 4, cellH - 4);
                        ctx.restore();
                    }

                    // Index badge (1, 2, 3...)
                    ctx.fillStyle = "rgba(0,0,0,0.75)";
                    ctx.fillRect(x + 4, y + 4, 18, 18);
                    ctx.fillStyle = "#fff";
                    ctx.font = "bold 10px sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(`${idx + 1}`, x + 13, y + 17);
                });
            };
        }
    }
});