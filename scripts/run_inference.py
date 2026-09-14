#!/usr/bin/env python3
"""Run OCR inference on a real document image using PaddleOCR-VL-1.6 on GPU."""

import argparse
import asyncio
import base64
import json
import os
import sys
import time

from ocr_service.backends import LocalPaddleOCRVLRecognition, WholePageLayout
from ocr_service.contracts import OCRMode
from ocr_service.service import OCRService
from ocr_service.settings import Settings


def parse_args():
    parser = argparse.ArgumentParser(description="Run PaddleOCR-VL inference on a test document.")
    parser.add_argument("--image", default="sample_vn_invoice.png", help="Path to input image")
    parser.add_argument("--model-id", default="PaddlePaddle/PaddleOCR-VL-1.6", help="HF model repository or local path")
    parser.add_argument("--device", default="cuda", help="Target device (cuda or cpu)")
    parser.add_argument("--output", default="ocr_output.json", help="Path to write JSON output")
    return parser.parse_args()


async def main_async(args):
    if not os.path.exists(args.image):
        print(f"Error: image file '{args.image}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Target image: {args.image}")
    print(f"Model ID: {args.model_id}")
    print(f"Device: {args.device}")

    settings = Settings(
        model_id=args.model_id,
        model_revision="paddleocr-vl-1.6",
        vllm_base_url="http://localhost:8000/v1",
        vllm_model_name="PaddleOCR-VL-1.6-0.9B",
        max_document_bytes=26214400,
        request_timeout_seconds=120.0,
        recognition_backend="local",
        device=args.device,
    )

    print("Initializing layout and local PaddleOCR-VL recognition backend...")
    layout_backend = WholePageLayout()
    recognition_backend = LocalPaddleOCRVLRecognition(model_id=args.model_id, device=args.device)
    service = OCRService(settings, layout_backend, recognition_backend)

    with open(args.image, "rb") as f:
        image_bytes = f.read()
    b64_content = base64.b64encode(image_bytes).decode("ascii")

    print(f"Running OCR processing pipeline on {args.image}...")
    start_time = time.time()
    result = await service.process(
        encoded=b64_content,
        filename=os.path.basename(args.image),
        mode=OCRMode.VLM,
    )
    elapsed = time.time() - start_time

    print(f"\nInference completed successfully in {elapsed:.2f} seconds!")
    print("\n" + "=" * 50)
    print("EXTRACTED MARKDOWN TEXT:")
    print("=" * 50)
    print(result.markdown)
    print("=" * 50)

    output_dict = result.model_dump()
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
    print(f"\nSaved structured OCR response to '{args.output}'.")


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
