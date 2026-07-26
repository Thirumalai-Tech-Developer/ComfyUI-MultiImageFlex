import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "FlexibleMultiImageUploader.Extension",
    async nodeCreated(node) {
        if (node.comfyClass === "FlexibleMultiImageUploader") {
            node.uploadedImages = []; // Array of { name, displayName, imgElement }

            // Hide raw JSON widget from UI
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
                const rowHeight = 52;
                const baseHeight = 95;
                node.size[0] = Math.max(node.size[0], 280);
                node.size[1] = baseHeight + (count * rowHeight);
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

                        node.uploadedImages.push({
                            name: fullPath,
                            displayName: filename,
                            imgElement: img
                        });
                        updateJsonWidget();
                        updateNodeSize();
                    }
                } catch (error) {
                    console.error("Upload failed:", error);
                }
            };

            // Single Upload Button (supports picking 1 or multiple files)
            node.addWidget("button", "📤 Upload Image(s)", null, () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "image/*";
                input.multiple = true; // Multi-image support
                input.onchange = async () => {
                    if (input.files && input.files.length > 0) {
                        for (const file of input.files) {
                            await uploadFile(file);
                        }
                    }
                };
                input.click();
            });

            // Handle clicking the ❌ remove button on individual list items
            const origOnMouseDown = node.onMouseDown;
            node.onMouseDown = function (e, pos, canvas) {
                if (this.flags.collapsed) return origOnMouseDown?.apply(this, arguments);

                const padding = 10;
                const startY = 85;
                const rowH = 48;
                const gap = 4;
                const btnW = 24;
                const btnH = 24;

                const count = this.uploadedImages ? this.uploadedImages.length : 0;

                for (let i = 0; i < count; i++) {
                    const y = startY + i * (rowH + gap);
                    const btnX = this.size[0] - padding - btnW;
                    const btnY = y + (rowH - btnH) / 2;

                    // Check if click hits the remove button bounding box
                    if (pos[0] >= btnX && pos[0] <= btnX + btnW && pos[1] >= btnY && pos[1] <= btnY + btnH) {
                        this.uploadedImages.splice(i, 1); // Remove item
                        updateJsonWidget();
                        updateNodeSize();
                        return true; // Click handled
                    }
                }

                return origOnMouseDown?.apply(this, arguments);
            };

            // Render vertical list on canvas
            const origDrawForeground = node.onDrawForeground;
            node.onDrawForeground = function (ctx) {
                if (origDrawForeground) origDrawForeground.apply(this, arguments);
                if (this.flags.collapsed) return;

                const count = this.uploadedImages ? this.uploadedImages.length : 0;
                if (count === 0) {
                    ctx.fillStyle = "#888";
                    ctx.font = "12px sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText("No images uploaded. Click above to add.", this.size[0] / 2, this.size[1] - 15);
                    return;
                }

                const padding = 10;
                const startY = 85;
                const rowH = 48;
                const gap = 4;
                const thumbSize = 40;

                this.uploadedImages.forEach((item, idx) => {
                    const y = startY + idx * (rowH + gap);
                    const rowW = this.size[0] - (padding * 2);

                    // Row background bar
                    ctx.fillStyle = "#1e1e1e";
                    ctx.strokeStyle = "#333";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    if (ctx.roundRect) ctx.roundRect(padding, y, rowW, rowH, 6);
                    else ctx.rect(padding, y, rowW, rowH);
                    ctx.fill();
                    ctx.stroke();

                    // Thumbnail image
                    const thumbX = padding + 4;
                    const thumbY = y + (rowH - thumbSize) / 2;

                    ctx.fillStyle = "#111";
                    ctx.fillRect(thumbX, thumbY, thumbSize, thumbSize);

                    if (item.imgElement && item.imgElement.complete && item.imgElement.naturalWidth > 0) {
                        ctx.save();
                        ctx.beginPath();
                        if (ctx.roundRect) ctx.roundRect(thumbX, thumbY, thumbSize, thumbSize, 4);
                        else ctx.rect(thumbX, thumbY, thumbSize, thumbSize);
                        ctx.clip();
                        ctx.drawImage(item.imgElement, thumbX, thumbY, thumbSize, thumbSize);
                        ctx.restore();
                    }

                    // Index + Filename text
                    ctx.fillStyle = "#ddd";
                    ctx.font = "11px sans-serif";
                    ctx.textAlign = "left";
                    
                    let text = `${idx + 1}. ${item.displayName}`;
                    const maxTextW = this.size[0] - padding * 2 - thumbSize - 45;
                    if (ctx.measureText(text).width > maxTextW) {
                        text = text.substring(0, 18) + "...";
                    }
                    ctx.fillText(text, thumbX + thumbSize + 8, y + (rowH / 2) + 4);

                    // Individual Remove Button (❌)
                    const btnW = 24;
                    const btnH = 24;
                    const btnX = this.size[0] - padding - btnW - 4;
                    const btnY = y + (rowH - btnH) / 2;

                    ctx.fillStyle = "#8d2525";
                    ctx.beginPath();
                    if (ctx.roundRect) ctx.roundRect(btnX, btnY, btnW, btnH, 4);
                    else ctx.rect(btnX, btnY, btnW, btnH);
                    ctx.fill();

                    ctx.fillStyle = "#ffffff";
                    ctx.font = "bold 12px sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText("✕", btnX + (btnW / 2), btnY + (btnH / 2) + 4);
                });
            };
        }
    }
});