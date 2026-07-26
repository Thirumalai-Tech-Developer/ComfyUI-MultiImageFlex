import os
import json
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths

class FlexibleMultiImageUploader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Receives the JSON list of uploaded filenames from the UI
                "image_list_json": ("STRING", {"default": "[]", "multiline": True}),
                "match_size_method": (["crop", "stretch", "pad"], {"default": "crop"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("image_batch", "count")
    FUNCTION = "process_images"
    CATEGORY = "image/upload"

    @classmethod
    def IS_CHANGED(cls, image_list_json, **kwargs):
        return image_list_json

    def process_images(self, image_list_json, match_size_method="crop"):
        try:
            filenames = json.loads(image_list_json)
        except Exception:
            filenames = []

        if not filenames:
            raise ValueError("No images uploaded yet. Click '📤 Upload Image' on the node.")

        collected_tensors = []

        for filename in filenames:
            if not filename or filename == "None" or filename.lower() == "example.png":
                continue

            try:
                file_path = folder_paths.get_annotated_filepath(filename)
            except Exception:
                continue

            if not os.path.exists(file_path):
                continue

            img = Image.open(file_path)
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")

            # Convert to ComfyUI tensor: [1, H, W, 3]
            tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
            collected_tensors.append(tensor)

        if not collected_tensors:
            raise ValueError("No valid images found in the upload list.")

        # Baseline resolution set by the first uploaded image
        target_h = collected_tensors[0].shape[1]
        target_w = collected_tensors[0].shape[2]
        target_size = (target_w, target_h)

        processed_tensors = []

        # Auto-resize mismatched dimensions so batch stacking succeeds
        for tensor in collected_tensors:
            h, w = tensor.shape[1], tensor.shape[2]
            if (h, w) == (target_h, target_w):
                processed_tensors.append(tensor)
            else:
                arr = (tensor[0].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                pil_img = Image.fromarray(arr)

                if match_size_method == "crop":
                    pil_img = ImageOps.fit(pil_img, target_size, Image.Resampling.LANCZOS)
                elif match_size_method == "stretch":
                    pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
                elif match_size_method == "pad":
                    pil_img = ImageOps.pad(pil_img, target_size, color=(0, 0, 0))

                resized_tensor = torch.from_numpy(np.array(pil_img).astype(np.float32) / 255.0).unsqueeze(0)
                processed_tensors.append(resized_tensor)

        # Combine into single [B, H, W, 3] batch
        batched_tensor = torch.cat(processed_tensors, dim=0)

        return (batched_tensor, len(processed_tensors))

NODE_CLASS_MAPPINGS = {
    "FlexibleMultiImageUploader": FlexibleMultiImageUploader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FlexibleMultiImageUploader": "📤 Flexible Multi-Image Uploader"
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]