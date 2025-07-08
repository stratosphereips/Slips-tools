# Qwen Fine-tuning with Unsloth

A complete project setup for fine-tuning Qwen models using the Unsloth framework - 2x faster training with 70% less VRAM usage.

## Overview

This project provides a comprehensive framework for fine-tuning Qwen models using Unsloth, featuring:

- **Efficient Training**: 2x faster than standard methods with 70% less VRAM
- **4-bit Quantization**: Enables larger models on smaller GPUs
- **LoRA Adapters**: Parameter-efficient fine-tuning
- **Mixed Datasets**: Combines reasoning and conversational data
- **Multiple Formats**: Save models in various formats for different use cases

## Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Prepare Dataset

```bash
# Create a mixed dataset (75% reasoning, 25% conversational)
python prepare_data.py --dataset-type mixed --output-path mixed_dataset.json

# Or prepare a custom dataset
python prepare_data.py --dataset-type custom --custom-path your_data.json
```

### 3. Configure Training

Edit `config.yaml` to adjust:
- Model size (4B, 8B, 14B, 32B)
- Training parameters
- Hardware-specific settings
- Output formats

### 4. Start Training

```bash
# Run training with default config
python train_qwen.py

# Or with custom config
python train_qwen.py --config custom_config.yaml
```

### 5. Use Jupyter Notebook

```bash
# Launch Jupyter
jupyter notebook

# Open qwen_finetuning_example.ipynb
```

## Project Structure

```
unsloth-ex/
├── requirements.txt              # Python dependencies
├── config.yaml                   # Training configuration
├── train_qwen.py                 # Main training script
├── prepare_data.py               # Dataset preparation
├── qwen_finetuning_example.ipynb # Interactive notebook
└── README.md                     # This file
```

## Configuration

### Model Options

| Model | VRAM Required | Context Length | Parameters |
|-------|---------------|----------------|------------|
| Qwen3-4B | 8GB | 2048+ | 4B |
| Qwen3-8B | 12GB | 2048+ | 8B |
| Qwen3-14B | 16GB | 2048+ | 14B |
| Qwen3-32B | 24GB+ | 2048+ | 32B |

### Hardware Recommendations

- **16GB GPU**: Qwen3-14B with batch_size=2
- **24GB GPU**: Qwen3-14B with batch_size=4 or Qwen3-32B with batch_size=2
- **40GB+ GPU**: Qwen3-32B with larger batch sizes

## Dataset Preparation

### Supported Formats

1. **Alpaca Format**: Instruction-input-output format
2. **Reasoning Dataset**: Math/logic problems with step-by-step solutions
3. **Conversational**: Multi-turn conversations
4. **Custom JSON**: Your own dataset format

### Mixed Dataset Strategy

Following Unsloth's recommendations:
- 75% reasoning data (e.g., math problems)
- 25% conversational data (e.g., general chat)

This maintains reasoning capabilities while improving conversational skills.

## Training Features

### LoRA Configuration

```yaml
lora_r: 16                    # Rank of adaptation
lora_alpha: 16                # Scaling parameter
lora_dropout: 0.1             # Dropout rate
target_modules:               # Modules to adapt
  - q_proj
  - k_proj
  - v_proj
  - o_proj
```

### Optimization Features

- **4-bit Quantization**: Reduces memory usage
- **Gradient Checkpointing**: Saves memory during training
- **Mixed Precision**: FP16/BF16 for faster training
- **8-bit Optimizer**: AdamW with 8-bit quantization

## Model Saving Options

1. **LoRA Only**: Save only the adapter weights
2. **Merged 16-bit**: Full model in 16-bit precision
3. **Merged 4-bit**: Full model in 4-bit precision
4. **GGUF Format**: For deployment with llama.cpp

## Advanced Usage

### Custom Dataset

```python
# Your dataset should be in conversation format
data = [
    {
        "conversation": [
            {"role": "user", "content": "Question here"},
            {"role": "assistant", "content": "Answer here"}
        ]
    }
]
```

### Multiple GPU Training

```bash
# Use torchrun for multi-GPU training
torchrun --nproc_per_node=2 train_qwen.py
```

### Weights & Biases Integration

```yaml
use_wandb: true
wandb:
  project: "qwen-finetuning"
  run_name: "qwen3-14b-experiment"
```

## Troubleshooting

### Common Issues

1. **Out of Memory**: Reduce batch size or use smaller model
2. **Slow Training**: Enable BF16 if supported by your GPU
3. **Import Errors**: Ensure all dependencies are installed

### Memory Optimization

```python
# Reduce memory usage
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
max_seq_length: 1024
```

## Performance Benchmarks

| Method | Speed | Memory | Accuracy |
|--------|-------|--------|----------|
| Standard | 1x | 100% | 100% |
| Unsloth | 2x | 30% | 100% |

## Examples

### Quick Training

```bash
# Train on small dataset for testing
python train_qwen.py --config config.yaml
```

### Production Training

```bash
# Full training with monitoring
python train_qwen.py --config production_config.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## References

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth Documentation](https://docs.unsloth.ai/)
- [Qwen Model Documentation](https://huggingface.co/Qwen)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Unsloth documentation
3. Open an issue on GitHub
4. Join the Unsloth Discord community