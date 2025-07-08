#!/usr/bin/env python3
"""
Dataset preparation script for Qwen fine-tuning
Handles data loading, formatting, and preprocessing for various dataset types.
"""

import json
import pandas as pd
from datasets import Dataset, load_dataset
from typing import List, Dict, Any, Optional
import argparse

def load_alpaca_dataset(dataset_name: str = "tatsu-lab/alpaca", split: str = "train") -> Dataset:
    """Load Alpaca-style instruction dataset."""
    dataset = load_dataset(dataset_name, split=split)
    
    def format_alpaca(examples):
        conversations = []
        for instruction, input_text, output in zip(
            examples["instruction"], examples["input"], examples["output"]
        ):
            conversation = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": instruction + (f"\n\n{input_text}" if input_text else "")},
                {"role": "assistant", "content": output}
            ]
            conversations.append(conversation)
        return {"conversation": conversations}
    
    return dataset.map(format_alpaca, batched=True)

def load_reasoning_dataset(dataset_name: str = "nvidia/OpenMathReasoning", split: str = "train") -> Dataset:
    """Load reasoning dataset (e.g., math reasoning)."""
    dataset = load_dataset(dataset_name, split=split)
    
    def format_reasoning(examples):
        conversations = []
        for problem, solution in zip(examples["problem"], examples["solution"]):
            conversation = [
                {"role": "system", "content": "You are a helpful assistant that provides step-by-step reasoning."},
                {"role": "user", "content": problem},
                {"role": "assistant", "content": solution}
            ]
            conversations.append(conversation)
        return {"conversation": conversations}
    
    return dataset.map(format_reasoning, batched=True)

def load_conversational_dataset(dataset_name: str = "Maxime/FineTome", split: str = "train") -> Dataset:
    """Load conversational dataset."""
    dataset = load_dataset(dataset_name, split=split)
    
    def format_conversational(examples):
        conversations = []
        for conv in examples["conversations"]:
            if isinstance(conv, list) and len(conv) > 0:
                conversation = []
                for turn in conv:
                    if "from" in turn and "value" in turn:
                        role = "user" if turn["from"] == "human" else "assistant"
                        conversation.append({"role": role, "content": turn["value"]})
                if conversation:
                    conversations.append(conversation)
        return {"conversation": conversations}
    
    return dataset.map(format_conversational, batched=True)

def load_custom_json_dataset(file_path: str) -> Dataset:
    """Load custom JSON dataset with conversation format."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Ensure data is in the expected format
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    
    conversations = []
    for item in data:
        if "conversation" in item:
            conversations.append(item["conversation"])
        elif "messages" in item:
            conversations.append(item["messages"])
        else:
            # Try to convert other formats
            conversation = []
            if "instruction" in item and "output" in item:
                conversation.append({"role": "user", "content": item["instruction"]})
                conversation.append({"role": "assistant", "content": item["output"]})
            conversations.append(conversation)
    
    return Dataset.from_dict({"conversation": conversations})

def mix_datasets(datasets: List[Dataset], ratios: List[float]) -> Dataset:
    """Mix multiple datasets according to specified ratios."""
    if len(datasets) != len(ratios):
        raise ValueError("Number of datasets must match number of ratios")
    
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError("Ratios must sum to 1.0")
    
    mixed_conversations = []
    
    for dataset, ratio in zip(datasets, ratios):
        num_samples = int(len(dataset) * ratio)
        sampled_dataset = dataset.shuffle(seed=42).select(range(min(num_samples, len(dataset))))
        mixed_conversations.extend(sampled_dataset["conversation"])
    
    return Dataset.from_dict({"conversation": mixed_conversations})

def create_mixed_dataset(
    reasoning_ratio: float = 0.75,
    conversational_ratio: float = 0.25,
    output_path: str = "mixed_dataset.json"
) -> Dataset:
    """Create a mixed dataset following Unsloth's recommended 75-25 split."""
    print("Loading reasoning dataset...")
    reasoning_dataset = load_reasoning_dataset()
    
    print("Loading conversational dataset...")
    conversational_dataset = load_conversational_dataset()
    
    print("Mixing datasets...")
    mixed_dataset = mix_datasets(
        [reasoning_dataset, conversational_dataset],
        [reasoning_ratio, conversational_ratio]
    )
    
    # Save to file
    mixed_dataset.to_json(output_path)
    print(f"Mixed dataset saved to {output_path}")
    print(f"Total samples: {len(mixed_dataset)}")
    
    return mixed_dataset

def validate_dataset(dataset: Dataset) -> Dict[str, Any]:
    """Validate dataset format and return statistics."""
    stats = {
        "total_samples": len(dataset),
        "avg_conversation_length": 0,
        "empty_conversations": 0,
        "roles_distribution": {},
        "sample_conversations": []
    }
    
    total_turns = 0
    for i, conversation in enumerate(dataset["conversation"]):
        if not conversation:
            stats["empty_conversations"] += 1
            continue
        
        total_turns += len(conversation)
        
        # Count roles
        for turn in conversation:
            role = turn.get("role", "unknown")
            stats["roles_distribution"][role] = stats["roles_distribution"].get(role, 0) + 1
        
        # Save first 3 conversations as samples
        if i < 3:
            stats["sample_conversations"].append(conversation)
    
    stats["avg_conversation_length"] = total_turns / len(dataset) if len(dataset) > 0 else 0
    
    return stats

def main():
    """Main function for dataset preparation."""
    parser = argparse.ArgumentParser(description="Prepare dataset for Qwen fine-tuning")
    parser.add_argument("--dataset-type", choices=["alpaca", "reasoning", "conversational", "mixed", "custom"], 
                       default="mixed", help="Type of dataset to prepare")
    parser.add_argument("--custom-path", type=str, help="Path to custom JSON dataset")
    parser.add_argument("--output-path", type=str, default="prepared_dataset.json", 
                       help="Output path for prepared dataset")
    parser.add_argument("--reasoning-ratio", type=float, default=0.75, 
                       help="Ratio of reasoning data in mixed dataset")
    parser.add_argument("--conversational-ratio", type=float, default=0.25, 
                       help="Ratio of conversational data in mixed dataset")
    parser.add_argument("--validate", action="store_true", help="Validate dataset after preparation")
    
    args = parser.parse_args()
    
    if args.dataset_type == "alpaca":
        dataset = load_alpaca_dataset()
    elif args.dataset_type == "reasoning":
        dataset = load_reasoning_dataset()
    elif args.dataset_type == "conversational":
        dataset = load_conversational_dataset()
    elif args.dataset_type == "mixed":
        dataset = create_mixed_dataset(args.reasoning_ratio, args.conversational_ratio, args.output_path)
    elif args.dataset_type == "custom":
        if not args.custom_path:
            raise ValueError("Custom dataset path is required for custom dataset type")
        dataset = load_custom_json_dataset(args.custom_path)
    else:
        raise ValueError(f"Unsupported dataset type: {args.dataset_type}")
    
    # Save dataset if not already saved
    if args.dataset_type != "mixed":
        dataset.to_json(args.output_path)
        print(f"Dataset saved to {args.output_path}")
    
    # Validate dataset if requested
    if args.validate:
        print("\nValidating dataset...")
        stats = validate_dataset(dataset)
        print(f"Dataset Statistics:")
        print(f"  Total samples: {stats['total_samples']}")
        print(f"  Average conversation length: {stats['avg_conversation_length']:.2f}")
        print(f"  Empty conversations: {stats['empty_conversations']}")
        print(f"  Roles distribution: {stats['roles_distribution']}")
        
        print("\nSample conversations:")
        for i, conv in enumerate(stats['sample_conversations']):
            print(f"  Sample {i+1}: {len(conv)} turns")
            for turn in conv[:2]:  # Show first 2 turns
                print(f"    {turn['role']}: {turn['content'][:100]}...")

if __name__ == "__main__":
    main()