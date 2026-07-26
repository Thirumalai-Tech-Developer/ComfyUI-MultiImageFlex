import os
import torch
import numpy as np
from PIL import Image, ImageOps

class FlexibleMultiImageLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "./input/my_images"}),
                # Determines how to handle images that don't match the first image's resolution
                "match_size_method": (["crop", "stretch", "pad"],), 
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("image_batch", "count")
    FUNCTION = "load_multi_images"
    CATEGORY = "image/batch"

    def load_multi_images(self, directory_path, match_size_method):
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            raise ValueError(f"Directory does not exist: {directory_path}")

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        files = sorted([
            os.path.join(directory_path, f) for f in os.listdir(directory_path)
            if os.path.splitext(f)[1].lower() in valid_exts
        ])

        if not files:
            raise ValueError(f"No valid image files found in {directory_path}")

        image_tensors = []
        target_size = None

        for i, file_path in enumerate(files):
            img = Image.open(file_path)
            img = ImageOps.exif_transpose(img) # Fix rotation metadata
            img = img.convert("RGB")

            # ComfyUI batches require all images to be the exact same resolution
            if i == 0:
                target_size = img.size # (width, height)
            else:
                if img.size != target_size:
                    if match_size_method == "crop":
                        img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
                    elif match_size_method == "stretch":
                        img = img.resize(target_size, Image.Resampling.LANCZOS)
                    elif match_size_method == "pad":
                        img = ImageOps.pad(img, target_size, color=(0, 0, 0))

            # Convert to ComfyUI tensor format: [1, H, W, 3], normalized to 0.0-1.0
            img_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
            image_tensors.append(img_tensor)

        # Concatenate all into a single batched tensor [B, H, W, 3]
        batched_tensor = torch.cat(image_tensors, dim=0)

        return (batched_tensor, len(image_tensors))

# Register the node in ComfyUI
NODE_CLASS_MAPPINGS = {
    "FlexibleMultiImageLoader": FlexibleMultiImageLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FlexibleMultiImageLoader": "📂 Flexible Multi-Image Loader"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]