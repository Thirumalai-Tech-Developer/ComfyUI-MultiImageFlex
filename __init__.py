import os
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths

class FlexibleMultiImageUploader:
    @classmethod
    def INPUT_TYPES(cls):
        # Fetch existing files in ComfyUI's input directory
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))] if os.path.exists(input_dir) else []
        
        return {
            "required": {
                # {"image_upload": True} triggers the native ComfyUI Upload Button widget!
                "image": (sorted(files), {"image_upload": True}),
                # Choose whether to pass only the selected image or all images in the upload folder
                "load_mode": (["single_image", "all_in_folder"], {"default": "single_image"}),
                # Auto-harmonize resolutions so PyTorch batching doesn't crash
                "match_size_method": (["crop", "stretch", "pad"], {"default": "crop"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("image_batch", "count")
    FUNCTION = "process_images"
    CATEGORY = "image/upload"

    @classmethod
    def IS_CHANGED(cls, image, load_mode, **kwargs):
        """Ensures ComfyUI re-executes whenever a new file is uploaded."""
        image_path = folder_paths.get_annotated_filepath(image)
        if load_mode == "single_image":
            return os.path.getmtime(image_path) if os.path.exists(image_path) else image
        else:
            parent_dir = os.path.dirname(image_path)
            if os.path.exists(parent_dir):
                return sum(os.path.getmtime(os.path.join(parent_dir, f)) 
                           for f in os.listdir(parent_dir) 
                           if os.path.isfile(os.path.join(parent_dir, f)))
            return image

    def process_images(self, image, load_mode, match_size_method):
        image_path = folder_paths.get_annotated_filepath(image)
        
        if not os.path.exists(image_path):
            raise ValueError(f"Uploaded image path does not exist: {image_path}")

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        files_to_process = []

        if load_mode == "single_image":
            files_to_process = [image_path]
        else:  # "all_in_folder" mode
            parent_dir = os.path.dirname(image_path)
            files_to_process = sorted([
                os.path.join(parent_dir, f) for f in os.listdir(parent_dir)
                if os.path.splitext(f)[1].lower() in valid_exts
            ])

        if not files_to_process:
            raise ValueError("No valid images found to process.")

        image_tensors = []
        target_size = None

        for i, file_path in enumerate(files_to_process):
            img = Image.open(file_path)
            img = ImageOps.exif_transpose(img)  # Fix EXIF orientation
            img = img.convert("RGB")

            # Set baseline size from the first image
            if i == 0:
                target_size = img.size  # (width, height)
            else:
                if img.size != target_size:
                    if match_size_method == "crop":
                        img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
                    elif match_size_method == "stretch":
                        img = img.resize(target_size, Image.Resampling.LANCZOS)
                    elif match_size_method == "pad":
                        img = ImageOps.pad(img, target_size, color=(0, 0, 0))

            # Convert to ComfyUI tensor: [1, H, W, 3] in 0.0 - 1.0 range
            tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
            image_tensors.append(tensor)

        # Combine into a single batch [B, H, W, 3]
        batched_tensor = torch.cat(image_tensors, dim=0)

        return (batched_tensor, len(image_tensors))

# Node Registration
NODE_CLASS_MAPPINGS = {
    "FlexibleMultiImageUploader": FlexibleMultiImageUploader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FlexibleMultiImageUploader": "📤 Flexible Multi-Image Uploader"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]