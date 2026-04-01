#!/usr/bin/env python3
"""
Convert a merged 16-bit model to GGUF format for use with Ollama.

Usage:
    python3 convert_to_gguf.py <model_dir> [--quant q4_k_m] [--output output_dir]

Example:
    python3 convert_to_gguf.py ./outputs/qwen_merged_16bit
    python3 convert_to_gguf.py ./outputs/qwen_merged_16bit --quant q8_0 --output ./my_gguf
"""

import argparse
import os
import glob
import sys


QUANT_OPTIONS = ["q4_k_m", "q5_k_m", "q8_0", "f16", "q4_0", "q5_0", "q2_k", "q3_k_m"]


def parse_args():
    parser = argparse.ArgumentParser(description="Convert merged 16-bit model to GGUF for Ollama")
    parser.add_argument("model_dir", help="Path to the merged 16-bit model directory")
    parser.add_argument("--quant", default="q4_k_m", choices=QUANT_OPTIONS,
                        help="Quantization method (default: q4_k_m)")
    parser.add_argument("--output", default=None,
                        help="Output directory for GGUF files (default: <model_dir>_gguf)")
    return parser.parse_args()


def main():
    args = parse_args()

    model_dir = os.path.abspath(args.model_dir)
    if not os.path.isdir(model_dir):
        print(f"Error: model directory not found: {model_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output or model_dir + "_gguf"
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Model:      {model_dir}")
    print(f"Quant:      {args.quant}")
    print(f"Output dir: {output_dir}")
    print()

    from unsloth import FastLanguageModel

    print("Loading model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_dir,
        dtype=None,
        load_in_4bit=False,  # load full precision for accurate conversion
    )

    print(f"Saving GGUF ({args.quant})...")
    model.save_pretrained_gguf(output_dir, tokenizer, quantization_method=args.quant)

    gguf_files = glob.glob(os.path.join(output_dir, "*.gguf"))
    if not gguf_files:
        print("Warning: no .gguf file found in output dir after conversion.", file=sys.stderr)
        sys.exit(1)

    gguf_file = gguf_files[0]
    modelfile_path = os.path.join(output_dir, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(f"FROM ./{os.path.basename(gguf_file)}\n")

    print()
    print("Done.")
    print(f"  GGUF:      {gguf_file}")
    print(f"  Modelfile: {modelfile_path}")
    print()
    print("To load in Ollama:")
    print(f"  ollama create my-model -f {modelfile_path}")
    print(f"  ollama run my-model")


if __name__ == "__main__":
    main()
