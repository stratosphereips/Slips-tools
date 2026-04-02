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
import json
import os
import glob
import shutil
import sys


QUANT_OPTIONS = ["q4_k_m", "q5_k_m", "q8_0", "f16", "q4_0", "q5_0", "q2_k", "q3_k_m"]

# Ollama Modelfile TEMPLATE + stop tokens for known chat formats.
# {{ .System }} / {{ .Prompt }} / {{ .Response }} are Ollama's Go template variables.
CHAT_TEMPLATES = {
    "chatml": {
        "template": (
            "{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}"
            "<|im_start|>user\n{{ .Prompt }}<|im_end|>\n"
            "<|im_start|>assistant\n{{ .Response }}<|im_end|>\n"
        ),
        "stop": ["<|im_end|>", "<|endoftext|>"],
    },
    "llama3": {
        "template": (
            "{{ if .System }}<|start_header_id|>system<|end_header_id|>\n\n"
            "{{ .System }}<|eot_id|>{{ end }}"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            "{{ .Prompt }}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
            "{{ .Response }}<|eot_id|>"
        ),
        "stop": ["<|eot_id|>", "<|end_of_text|>"],
    },
}


def detect_chat_template(model_dir):
    """Detect chat template type from tokenizer_config.json. Returns a key from CHAT_TEMPLATES."""
    cfg_path = os.path.join(model_dir, "tokenizer_config.json")
    if not os.path.isfile(cfg_path):
        return "chatml"  # safe default for Qwen

    with open(cfg_path) as f:
        cfg = json.load(f)

    template = cfg.get("chat_template", "")
    if "<|im_start|>" in template:
        return "chatml"
    if "<|start_header_id|>" in template:
        return "llama3"
    # fallback
    return "chatml"


def write_modelfile(output_dir, gguf_filename, template_key):
    tmpl = CHAT_TEMPLATES[template_key]
    lines = [
        f"FROM ./{gguf_filename}",
        "",
        f'TEMPLATE """{ tmpl["template"] }"""',
        "",
    ]
    for stop_token in tmpl["stop"]:
        lines.append(f'PARAMETER stop "{stop_token}"')
    lines.append("")

    modelfile_path = os.path.join(output_dir, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write("\n".join(lines))
    return modelfile_path


def parse_args():
    parser = argparse.ArgumentParser(description="Convert merged 16-bit model to GGUF for Ollama")
    parser.add_argument("model_dir", help="Path to the merged 16-bit model directory")
    parser.add_argument("--quant", default="q4_k_m", choices=QUANT_OPTIONS,
                        help="Quantization method (default: q4_k_m)")
    parser.add_argument("--output", default=None,
                        help="Output directory for GGUF files (default: <model_dir>_gguf)")
    # Look for OLLAMA_README.md next to this script as default
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_readme = os.path.join(script_dir, "OLLAMA_README.md")
    parser.add_argument("--readme", default=default_readme if os.path.isfile(default_readme) else None,
                        help="Path to README.md to copy into the output dir for Ollama (default: OLLAMA_README.md next to this script)")
    return parser.parse_args()


def main():
    args = parse_args()

    model_dir = os.path.abspath(args.model_dir)
    if not os.path.isdir(model_dir):
        print(f"Error: model directory not found: {model_dir}", file=sys.stderr)
        sys.exit(1)

    # Unsloth's save_pretrained_gguf uses save_directory as input_folder for
    # conversion, then writes the GGUF into save_directory + "_gguf".
    # So we must pass model_dir as save_directory, and collect output from model_dir_gguf.
    unsloth_gguf_dir = model_dir + "_gguf"

    final_output_dir = os.path.abspath(args.output) if args.output else unsloth_gguf_dir

    print(f"Model:      {model_dir}")
    print(f"Quant:      {args.quant}")
    print(f"Output dir: {final_output_dir}")
    print()

    from unsloth import FastLanguageModel

    print("Loading model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_dir,
        dtype=None,
        load_in_4bit=False,  # load full precision for accurate conversion
    )

    print(f"Saving GGUF ({args.quant})...")
    # Pass model_dir so unsloth reads config.json from there; it writes GGUF to model_dir_gguf
    model.save_pretrained_gguf(model_dir, tokenizer, quantization_method=args.quant)

    gguf_files = glob.glob(os.path.join(unsloth_gguf_dir, "*.gguf"))
    if not gguf_files:
        print("Warning: no .gguf file found after conversion.", file=sys.stderr)
        sys.exit(1)

    # Move output to final_output_dir if different from unsloth_gguf_dir
    if os.path.abspath(final_output_dir) != os.path.abspath(unsloth_gguf_dir):
        os.makedirs(final_output_dir, exist_ok=True)
        moved = []
        for f in glob.glob(os.path.join(unsloth_gguf_dir, "*")):
            dest = os.path.join(final_output_dir, os.path.basename(f))
            shutil.move(f, dest)
            moved.append(dest)
        try:
            os.rmdir(unsloth_gguf_dir)
        except OSError:
            pass
        gguf_files = [f for f in moved if f.endswith(".gguf")]

    gguf_file = gguf_files[0]
    template_key = detect_chat_template(model_dir)
    print(f"Detected chat template: {template_key}")
    modelfile_path = write_modelfile(final_output_dir, os.path.basename(gguf_file), template_key)

    readme_path = None
    if args.readme:
        if os.path.isfile(args.readme):
            readme_path = os.path.join(final_output_dir, "README.md")
            shutil.copy2(args.readme, readme_path)
            print(f"Copied README: {readme_path}")
        else:
            print(f"Warning: README not found at {args.readme}, skipping.", file=sys.stderr)

    print()
    print("Done.")
    print(f"  GGUF:      {gguf_file}")
    print(f"  Modelfile: {modelfile_path}")
    if readme_path:
        print(f"  README:    {readme_path}")
    print()
    print("To load in Ollama:")
    print(f"  ollama create my-model -f {modelfile_path}")
    print(f"  ollama run my-model")


if __name__ == "__main__":
    main()
