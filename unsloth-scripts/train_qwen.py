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
from trl import SFTTrainer
from transformers import TrainingArguments
import wandb

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
    
    return model, tokenizer

def prepare_dataset(dataset_config, tokenizer):
    """Load and prepare the training dataset."""
    if dataset_config["type"] == "huggingface":
        dataset = load_dataset(dataset_config["name"], split=dataset_config["split"])
    elif dataset_config["type"] == "local":
        dataset = load_dataset("json", data_files=dataset_config["path"])["train"]
    else:
        raise ValueError(f"Unsupported dataset type: {dataset_config['type']}")
    
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
    
    return dataset

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
    
    # Prepare dataset
    print("Preparing dataset...")
    dataset = prepare_dataset(config["dataset"], tokenizer)
    
    # Set up training arguments
    training_args = TrainingArguments(
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
        save_total_limit=config["training"]["save_total_limit"],
        dataloader_num_workers=config["training"].get("dataloader_num_workers", 0),
        remove_unused_columns=False,
    )
    
    # Create trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=config["model"]["max_seq_length"],
        dataset_num_proc=config["training"].get("dataset_num_proc", 2),
        packing=config["training"].get("packing", False),
        args=training_args,
    )
    
    # Train the model
    print("Starting training...")
    trainer.train()
    
    # Save the model
    print("Saving model...")
    model.save_pretrained(config["training"]["output_dir"])
    tokenizer.save_pretrained(config["training"]["output_dir"])
    
    # Save model in different formats if specified
    if config["training"].get("save_method") == "merged_16bit":
        model.save_pretrained_merged(
            config["training"]["output_dir"] + "_merged_16bit",
            tokenizer,
            save_method="merged_16bit"
        )
    elif config["training"].get("save_method") == "merged_4bit":
        model.save_pretrained_merged(
            config["training"]["output_dir"] + "_merged_4bit",
            tokenizer,
            save_method="merged_4bit"
        )
    elif config["training"].get("save_method") == "lora":
        model.save_pretrained_gguf(
            config["training"]["output_dir"] + "_lora",
            tokenizer,
            quantization_method="q4_k_m"
        )
    
    print("Training completed successfully!")

if __name__ == "__main__":
    main()