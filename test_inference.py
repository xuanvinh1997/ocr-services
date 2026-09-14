import os
import time
import json
import torch
from PIL import Image
import transformers.masking_utils

_orig_create_causal_mask = transformers.masking_utils.create_causal_mask
def _patched_create_causal_mask(*args, **kwargs):
    if "inputs_embeds" in kwargs and "input_embeds" not in kwargs:
        kwargs["input_embeds"] = kwargs.pop("inputs_embeds")
    return _orig_create_causal_mask(*args, **kwargs)
transformers.masking_utils.create_causal_mask = _patched_create_causal_mask

from transformers import AutoModelForCausalLM, AutoProcessor

model_id = "PaddlePaddle/PaddleOCR-VL-1.6"
print("Loading processor...")
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

print("Loading model to CUDA...")
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16
).to("cuda")
print(f"Model loaded in {time.time() - t0:.2f}s")

image_path = "sample_vn_invoice.png"
if os.path.exists(image_path):
    image = Image.open(image_path).convert("RGB")
    print(f"Loaded image: {image.size}")
else:
    print("Image not found!")
    exit(1)

messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": "OCR with layout:"}
        ]
    }
]

text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=[text], images=[image], return_tensors="pt")
inputs = {k: v.to("cuda") if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

print("Running inference on RTX 5060 Ti GPU...")
t_inf = time.time()
with torch.inference_mode():
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=False,
    )
latency = time.time() - t_inf

generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
decoded = processor.decode(generated_ids, skip_special_tokens=True)

# Write to file with utf-8 encoding
output_file = "ocr_result.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(decoded)

print(f"Inference completed in {latency:.2f}s")
print("Decoded raw representation:")
print(repr(decoded))
print("\n--- DECODED TEXT ---")
print(decoded)
print("--- END DECODED TEXT ---")


