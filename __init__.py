import os
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths

class FlexibleMultiImageUploader:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))] if os.path.exists(input_dir) else []
        sorted_files = sorted(files)

        # Pre-define optional upload slots
        optional_inputs = {}
        for i in range(2, 11):
            optional_inputs[f"image_{i}"] = (sorted_files, {"image_upload": True})

        return {
            "required": {
                # Primary upload slot with native ComfyUI Upload button
                "image_1": (sorted_files, {"image_upload": True}),
                "match_size_method": (["crop", "stretch", "pad"], {"default": "crop"}),
            },
            "optional": optional_inputs
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("image_batch", "count")
    FUNCTION = "process_images"
    CATEGORY = "image/upload"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Forces ComfyUI execution when uploaded files change."""
        mtimes = []
        for key, val in kwargs.items():
            if isinstance(val, str) and val:
                try:
                    path = folder_paths.get_annotated_filepath(val)
                    if os.path.exists(path):
                        mtimes.append(os.path.getmtime(path))
                except Exception:
                    pass
        return sum(mtimes) if mtimes else float("nan")

    def process_images(self, match_size_method="crop", **kwargs):
        # Sort image inputs numerically (image_1, image_2, image_3...)
        image_keys = sorted(
            [k for k in kwargs.keys() if k.startswith("image_")],
            key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 999
        )

        collected_tensors = []

        for key in image_keys:
            val = kwargs[key]
            if val is None or val == "":
                continue

            # Handle direct image tensor input [B, H, W, C]
            if isinstance(val, torch.Tensor):
                tensor = val
                if tensor.ndim == 3:
                    tensor = tensor.unsqueeze(0)
                for b in range(tensor.shape[0]):
                    collected_tensors.append(tensor[b:b+1])

            # Handle uploaded filename from ComfyUI input directory
            elif isinstance(val, str):
                try:
                    file_path = folder_paths.get_annotated_filepath(val)
                except Exception:
                    continue

                if not os.path.exists(file_path):
                    continue

                img = Image.open(file_path)
                img = ImageOps.exif_transpose(img)
                img = img.convert("RGB")

                # Convert to standard ComfyUI float32 tensor [1, H, W, 3]
                tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
                collected_tensors.append(tensor)

        if not collected_tensors:
            raise ValueError("No images were uploaded or connected.")

        # Establish baseline dimensions from first image
        target_h = collected_tensors[0].shape[1]
        target_w = collected_tensors[0].shape[2]
        target_size = (target_w, target_h)

        processed_tensors = []

        # Auto-resize mismatched dimensions so batch tensor stacking doesn't crash
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

        # Concatenate into single batch tensor [B, H, W, 3]
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