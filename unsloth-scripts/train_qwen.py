#!/usr/bin/env python3
"""
Qwen Model Fine-tuning with Unsloth
Main training script for fine-tuning Qwen models using the Unsloth framework.
"""

import os
import yaml
import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template, train_on_responses_only
from trl import SFTTrainer, SFTConfig
import wandb

# DPO/ORPO imports are deferred to avoid loading unnecessary classes
# when running in SFT mode.

def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_model_and_tokenizer(model_config):
    """Load Qwen model and tokenizer with Unsloth optimizations."""
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["model_name"],
        max_seq_length=model_config["max_seq_length"],
        dtype=model_config.get("dtype", None),
        load_in_4bit=model_config.get("load_in_4bit", True),
        device_map=model_config.get("device_map", "auto"),
    )
    
    # Add LoRA adapters for efficient fine-tuning
    model = FastLanguageModel.get_peft_model(
        model,
        r=model_config.get("lora_r", 16),
        target_modules=model_config.get("lora_targets", [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ]),
        lora_alpha=model_config.get("lora_alpha", 16),
        lora_dropout=model_config.get("lora_dropout", 0.1),
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=model_config.get("random_state", 42),
        use_rslora=model_config.get("use_rslora", False),
        loftq_config=model_config.get("loftq_config", None),
    )
    
    # Set chat template for the tokenizer
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

    return model, tokenizer

def prepare_dataset(dataset_config, tokenizer, eval_path=None):
    """Load and prepare the training dataset, and optionally an eval dataset."""
    if dataset_config["type"] == "huggingface":
        dataset = load_dataset(dataset_config["name"], split=dataset_config["split"])
    elif dataset_config["type"] == "local":
        dataset = load_dataset("json", data_files=dataset_config["path"])["train"]
    else:
        raise ValueError(f"Unsupported dataset type: {dataset_config['type']}")

    eval_dataset = None
    if eval_path:
        eval_dataset = load_dataset("json", data_files=eval_path)["train"]

    # Format dataset for chat template
    def format_chat_template(examples):
        texts = []
        for conversation in examples[dataset_config["text_column"]]:
            text = tokenizer.apply_chat_template(
                conversation,
                tokenize=False,
                add_generation_prompt=False
            )
            texts.append(text)
        return {"text": texts}

    if dataset_config.get("use_chat_template", True):
        dataset = dataset.map(format_chat_template, batched=True)
        if eval_dataset is not None:
            eval_dataset = eval_dataset.map(format_chat_template, batched=True)

    return dataset, eval_dataset

def load_preference_dataset(dataset_config):
    """Load DPO/ORPO preference datasets (prompt/chosen/rejected format)."""
    train = load_dataset("json", data_files=dataset_config["dpo_train_path"])["train"]
    eval_ = None
    if dataset_config.get("dpo_eval_path"):
        eval_ = load_dataset("json", data_files=dataset_config["dpo_eval_path"])["train"]
    return train, eval_


def train_dpo(config, model, tokenizer):
    """Run DPO or ORPO preference training."""
    from trl import DPOTrainer, ORPOTrainer
    from trl import DPOConfig, ORPOConfig

    dpo_cfg = config["training"]
    mode = dpo_cfg["mode"]  # "dpo" or "orpo"

    train_ds, eval_ds = load_preference_dataset(config["dataset"])

    eval_cfg = config.get("evaluation", {})

    if mode == "dpo":
        trainer_cls = DPOTrainer
        trainer_config = DPOConfig(
            beta=config["dpo"].get("beta", 0.1),
            output_dir=dpo_cfg["output_dir"] + "_dpo",
            num_train_epochs=dpo_cfg["num_train_epochs"],
            per_device_train_batch_size=dpo_cfg["per_device_train_batch_size"],
            gradient_accumulation_steps=dpo_cfg["gradient_accumulation_steps"],
            learning_rate=dpo_cfg.get("dpo_learning_rate", dpo_cfg["learning_rate"]),
            eval_strategy="steps" if eval_ds is not None else "no",
            eval_steps=eval_cfg.get("eval_steps", 50) if eval_ds is not None else None,
            save_steps=dpo_cfg["save_steps"],
            save_total_limit=eval_cfg.get("save_total_limit", 2),
            logging_steps=dpo_cfg["logging_steps"],
            seed=dpo_cfg["seed"],
            report_to=dpo_cfg.get("report_to", []),
            max_length=config["model"]["max_seq_length"],
        )
    else:  # orpo
        trainer_cls = ORPOTrainer
        trainer_config = ORPOConfig(
            lambda_=config["dpo"].get("orpo_lambda", 0.1),
            output_dir=dpo_cfg["output_dir"] + "_orpo",
            num_train_epochs=dpo_cfg["num_train_epochs"],
            per_device_train_batch_size=dpo_cfg["per_device_train_batch_size"],
            gradient_accumulation_steps=dpo_cfg["gradient_accumulation_steps"],
            learning_rate=dpo_cfg.get("dpo_learning_rate", dpo_cfg["learning_rate"]),
            eval_strategy="steps" if eval_ds is not None else "no",
            eval_steps=eval_cfg.get("eval_steps", 50) if eval_ds is not None else None,
            save_steps=dpo_cfg["save_steps"],
            save_total_limit=eval_cfg.get("save_total_limit", 2),
            logging_steps=dpo_cfg["logging_steps"],
            seed=dpo_cfg["seed"],
            report_to=dpo_cfg.get("report_to", []),
            max_length=config["model"]["max_seq_length"],
        )

    trainer = trainer_cls(
        model=model,
        args=trainer_config,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
    )
    trainer.train()
    return trainer


def main():
    """Main training function."""
    # Load configuration
    config = load_config()
    
    # Initialize wandb if enabled
    if config.get("use_wandb", False):
        wandb.init(
            project=config["wandb"]["project"],
            name=config["wandb"]["run_name"],
            config=config
        )
    
    # Load model and tokenizer
    print("Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(config["model"])
    
    mode = config["training"].get("mode", "sft")

    if mode == "sft":
        # Prepare dataset
        print("Preparing dataset...")
        eval_path = config["dataset"].get("eval_path")
        dataset, eval_dataset = prepare_dataset(config["dataset"], tokenizer, eval_path=eval_path)

        eval_cfg = config.get("evaluation", {})
        eval_steps = eval_cfg.get("eval_steps", 50)
        save_total_limit = eval_cfg.get("save_total_limit", config["training"].get("save_total_limit", 2))
        load_best_model_at_end = eval_cfg.get("load_best_model_at_end", False) and eval_dataset is not None

        # Set up training arguments
        training_args = SFTConfig(
            per_device_train_batch_size=config["training"]["per_device_train_batch_size"],
            gradient_accumulation_steps=config["training"]["gradient_accumulation_steps"],
            warmup_steps=config["training"]["warmup_steps"],
            num_train_epochs=config["training"]["num_train_epochs"],
            max_steps=config["training"].get("max_steps", -1),
            learning_rate=config["training"]["learning_rate"],
            fp16=config["training"].get("fp16", not torch.cuda.is_bf16_supported()),
            bf16=config["training"].get("bf16", torch.cuda.is_bf16_supported()),
            logging_steps=config["training"]["logging_steps"],
            optim=config["training"]["optimizer"],
            weight_decay=config["training"]["weight_decay"],
            lr_scheduler_type=config["training"]["lr_scheduler_type"],
            seed=config["training"]["seed"],
            output_dir=config["training"]["output_dir"],
            report_to=config["training"].get("report_to", []),
            save_steps=config["training"]["save_steps"],
            save_total_limit=save_total_limit,
            dataloader_num_workers=config["training"].get("dataloader_num_workers", 0),
            remove_unused_columns=False,
            eval_strategy="steps" if eval_dataset is not None else "no",
            eval_steps=eval_steps if eval_dataset is not None else None,
            metric_for_best_model=eval_cfg.get("metric_for_best_model", "loss") if eval_dataset is not None else None,
            load_best_model_at_end=load_best_model_at_end,
            dataset_text_field="text",
            max_length=config["model"]["max_seq_length"],
            dataset_num_proc=config["training"].get("dataset_num_proc", 2),
            packing=config["training"].get("packing", False),
        )

        # Create trainer
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            eval_dataset=eval_dataset,
            args=training_args,
        )

        # Mask loss on instruction tokens — train only on assistant responses
        trainer = train_on_responses_only(
            trainer,
            instruction_part="<|im_start|>user\n",
            response_part="<|im_start|>assistant\n",
        )

        # Train the model
        print("Starting training...")
        trainer.train()

        # Save the model
        print("Saving model...")
        model.save_pretrained(config["training"]["output_dir"])
        tokenizer.save_pretrained(config["training"]["output_dir"])

    elif mode in ("dpo", "orpo"):
        print(f"Starting {mode.upper()} training on SFT checkpoint...")
        trainer = train_dpo(config, model, tokenizer)
        model = trainer.model

        # Save the model
        print("Saving model...")
        dpo_output_dir = config["training"]["output_dir"] + f"_{mode}"
        model.save_pretrained(dpo_output_dir)
        tokenizer.save_pretrained(dpo_output_dir)

    else:
        raise ValueError(f"Unknown training mode: {mode!r}. Expected 'sft', 'dpo', or 'orpo'.")
    
    # Save model in different formats if specified
    save_method = config["training"].get("save_method")
    if save_method == "merged_16bit":
        model.save_pretrained_merged(
            config["training"]["output_dir"] + "_merged_16bit",
            tokenizer,
            save_method="merged_16bit"
        )
    elif save_method == "merged_4bit":
        model.save_pretrained_merged(
            config["training"]["output_dir"] + "_merged_4bit",
            tokenizer,
            save_method="merged_4bit"
        )
    elif save_method == "lora":
        model.save_pretrained_gguf(
            config["training"]["output_dir"] + "_lora",
            tokenizer,
            quantization_method="q4_k_m"
        )

    gguf_quantization = config["training"].get("gguf_quantization")
    if gguf_quantization:
        gguf_dir = config["training"]["output_dir"] + "_gguf"
        print(f"Saving GGUF ({gguf_quantization})...")
        model.save_pretrained_gguf(gguf_dir, tokenizer, quantization_method=gguf_quantization)
        # Write Modelfile for direct use with: ollama create <name> -f <gguf_dir>/Modelfile
        import glob as _glob, json as _json
        gguf_files = _glob.glob(f"{gguf_dir}/*.gguf")
        if gguf_files:
            # Detect chat template from tokenizer_config
            _cfg_path = os.path.join(config["training"]["output_dir"] + "_merged_16bit", "tokenizer_config.json")
            _cfg_path = _cfg_path if os.path.isfile(_cfg_path) else os.path.join(config["training"]["output_dir"], "tokenizer_config.json")
            _template = ""
            if os.path.isfile(_cfg_path):
                with open(_cfg_path) as _f:
                    _template = _json.load(_f).get("chat_template", "")
            _is_chatml = "<|im_start|>" in _template or not _template  # Qwen default
            _gguf_name = os.path.basename(gguf_files[0])
            if _is_chatml:
                _tmpl_block = (
                    '{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}'
                    '<|im_start|>user\n{{ .Prompt }}<|im_end|>\n'
                    '<|im_start|>assistant\n{{ .Response }}<|im_end|>'
                )
                _stop_tokens = ['<|im_end|>', '<|im_start|>']
            else:
                _tmpl_block = (
                    '{{ if .System }}<|start_header_id|>system<|end_header_id|>\n\n{{ .System }}<|eot_id|>{{ end }}'
                    '<|start_header_id|>user<|end_header_id|>\n\n{{ .Prompt }}<|eot_id|>'
                    '<|start_header_id|>assistant<|end_header_id|>\n\n{{ .Response }}<|eot_id|>'
                )
                _stop_tokens = ['<|eot_id|>', '<|end_of_text|>']
            with open(f"{gguf_dir}/Modelfile", "w") as f:
                f.write(f"FROM ./{_gguf_name}\n\nTEMPLATE \"\"\"{_tmpl_block}\"\"\"\n\n")
                for _s in _stop_tokens:
                    f.write(f'PARAMETER stop "{_s}"\n')
    
    print("Training completed successfully!")

if __name__ == "__main__":
    import torch._dynamo
    torch._dynamo.config.disable = True
    main()