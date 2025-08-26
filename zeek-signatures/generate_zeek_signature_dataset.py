#!/usr/bin/env python3
"""
Zeek Signature Dataset Generator

This script generates a dataset of Zeek signatures for LLM fine-tuning using the Alpaca format.
It creates diverse signature generation tasks by varying threat types, protocols, complexity levels,
and network contexts to ensure high variability in the training data.

Usage:
    # Generate 100 signatures with default settings
    python3 generate_zeek_signature_dataset.py --count 100 --output signatures_dataset.json
    
    # Print complete signatures to console during generation
    python3 generate_zeek_signature_dataset.py --count 10 --print-signatures
    
    # Use different model/endpoint
    python3 generate_zeek_signature_dataset.py --model gpt-4o --base_url https://api.openai.com/v1
    
    # Use external reference document for better signatures
    python3 generate_zeek_signature_dataset.py --count 50 --reference-doc zeek_examples.txt
"""

import json
import random
import argparse
import os
import sys
import re
import subprocess
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Add the benchmark_models directory to the path to import the LLM query script
benchmark_dir = Path(__file__).parent.parent / "benchmark_models"
sys.path.append(str(benchmark_dir))

try:
    from stream_query_llm_long_prompt import stream_chat_with_usage, load_prompt
except ImportError as e:
    print("❌ Import Error: Could not import stream_query_llm_long_prompt.py")
    print(f"   Expected location: {benchmark_dir / 'stream_query_llm_long_prompt.py'}")
    print(f"   Error details: {e}")
    print(f"   Note: This script is used for reference but the dataset generator has its own LLM interface")
    print(f"   You can continue using this script even without the import")
except Exception as e:
    print(f"❌ Unexpected import error: {type(e).__name__}")
    print(f"   Details: {e}")


class ZeekSignaturePromptGenerator:
    """Generates diverse prompts for Zeek signature creation with high variability."""
    
    def __init__(self, reference_content: str = None):
        self.reference_content = reference_content
        self.threat_types = [
            "malware command and control communication",
            "SQL injection attack",
            "cross-site scripting (XSS) payload",
            "remote code execution attempt",
            "brute force login attack",
            "DNS tunneling activity",
            "data exfiltration over HTTP",
            "port scanning behavior",
            "cryptocurrency mining malware",
            "ransomware communication",
            "phishing email content",
            "backdoor communication",
            "privilege escalation attempt",
            "buffer overflow exploit",
            "web shell upload",
            "credential harvesting",
            "lateral movement activity",
            "suspicious file download",
            "covert channel communication",
            "botnet activity"
        ]
        
        self.protocols = [
            "HTTP", "HTTPS", "DNS", "SSH", "FTP", "SMTP", 
            "TCP", "UDP", "TLS", "SMB", "ICMP"
        ]
        
        self.complexity_levels = [
            "simple payload pattern matching",
            "multi-field condition matching (IP, port, and payload)",
            "stateful TCP connection analysis",
            "HTTP header and body analysis",
            "regex-based content detection",
            "binary payload signature matching"
        ]
        
        self.network_contexts = [
            "enterprise network environment",
            "web server infrastructure",
            "DNS server traffic",
            "email server communications",
            "IoT device network",
            "cloud infrastructure",
            "remote access connections",
            "internal network traffic"
        ]
        
        self.signature_requirements = [
            "include proper signature metadata and event description",
            "use appropriate port matching for the protocol",
            "implement case-insensitive pattern matching",
            "include both source and destination criteria",
            "use efficient regex patterns to avoid performance issues",
            "provide descriptive event messages for analysts"
        ]

    def generate_prompt(self) -> Tuple[str, str]:
        """Generate a varied prompt for Zeek signature creation."""
        threat = random.choice(self.threat_types)
        protocol = random.choice(self.protocols)
        complexity = random.choice(self.complexity_levels)
        context = random.choice(self.network_contexts)
        requirement = random.choice(self.signature_requirements)
        
        # Create instruction
        instruction = f"Create a Zeek signature to detect {threat}"
        
        # Create input with context and requirements
        input_text = f"""Protocol: {protocol}
Network Context: {context}
Detection Method: {complexity}
Additional Requirement: {requirement}"""
        
        # Create detailed prompt for the LLM
        full_prompt = f"""Create a Zeek signature (.sig file format) to detect {threat} in {protocol} traffic within a {context}.

IMPORTANT: This is a Zeek signature (NOT a YARA rule). Use Zeek signature syntax only.

Requirements:
- Use proper Zeek signature syntax with signature name, conditions, and event description
- Implement {complexity}
- {requirement}
- The signature should be practical and avoid false positives

Zeek Signature Format Example:
signature example-malware {{
    ip-proto == tcp
    dst-port == 80
    payload /GET.*malware/
    event "Malware communication detected"
}}

Valid Zeek signature fields include:
- ip-proto (tcp, udp, icmp)
- src-ip, dst-ip (IP addresses or networks)
- src-port, dst-port (port numbers)
- payload (regex pattern in content)
- http-request, http-reply (HTTP-specific patterns)
- tcp-state (TCP connection state)
- event (description string)

DO NOT:
- Use markdown code blocks or formatting
- Use YARA rule syntax (id, condition, metadata blocks)
- Include explanatory text before or after the signature"""

        # Add reference documentation if provided
        if self.reference_content:
            full_prompt += f"""

Reference Documentation:
{self.reference_content}

Use the above reference material to guide your signature creation when applicable."""

        # Add final instruction
        full_prompt += """

Output ONLY the raw Zeek signature starting with 'signature' and ending with the closing brace."""
        
        return instruction, input_text, full_prompt

    def _preprocess_signature(self, signature: str) -> str:
        """Preprocess signature by removing markdown and cleaning up format."""
        # Remove markdown code blocks
        cleaned = re.sub(r'```\w*\n?', '', signature)
        cleaned = re.sub(r'```', '', cleaned)
        
        # Remove common markdown artifacts
        cleaned = re.sub(r'^\s*plaintext\s*\n', '', cleaned, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        cleaned = '\n'.join(line.strip() for line in cleaned.split('\n') if line.strip())
        
        return cleaned.strip()

    def validate_signature_syntax(self, signature: str) -> Tuple[bool, str, str]:
        """Basic validation of Zeek signature syntax. Returns (is_valid, message, processed_signature)."""
        if not signature.strip():
            return False, "❌ Empty signature output", ""
        
        # Preprocess: Strip markdown code blocks and clean up
        processed_signature = self._preprocess_signature(signature)
        
        # Check for basic signature structure
        if not processed_signature.strip().startswith('signature'):
            # Check if it looks like YARA format
            if 'rule ' in processed_signature or 'condition =' in processed_signature:
                return False, "❌ Generated YARA rule instead of Zeek signature", processed_signature
            # Check if it still has markdown
            if '```' in processed_signature:
                return False, "❌ Contains markdown code blocks - expected raw Zeek signature", processed_signature
            return False, "❌ Signature must start with 'signature' keyword", processed_signature
        
        if '{' not in processed_signature:
            return False, "❌ Missing opening brace '{' in signature", processed_signature
            
        if '}' not in processed_signature:
            return False, "❌ Missing closing brace '}' in signature", processed_signature
        
        # Check brace balance
        open_braces = processed_signature.count('{')
        close_braces = processed_signature.count('}')
        if open_braces != close_braces:
            return False, f"❌ Unbalanced braces: {open_braces} opening, {close_braces} closing", processed_signature
        
        # Check for signature name
        lines = processed_signature.strip().split('\n')
        first_line = lines[0].strip()
        if not re.match(r'signature\s+[\w-]+\s*{', first_line):
            return False, "❌ Invalid signature name format. Should be 'signature name-here {'", processed_signature
        
        # Check for valid Zeek signature components
        valid_fields = ['ip-proto', 'src-ip', 'dst-ip', 'src-port', 'dst-port', 
                       'payload', 'http-request', 'http-reply', 'tcp-state', 'event']
        
        has_valid_field = False
        for field in valid_fields:
            if field in processed_signature:
                has_valid_field = True
                break
        
        if not has_valid_field:
            return False, "❌ No valid Zeek signature fields found (ip-proto, payload, event, etc.)", processed_signature
        
        return True, f"✓ Valid Zeek signature syntax (processed from {len(signature)} to {len(processed_signature)} chars)", processed_signature


class ZeekDatasetGenerator:
    """Main class for generating the Zeek signature dataset."""
    
    def __init__(self, base_url: str = "https://api.openai.com/v1", 
                 model: str = "gpt-4o-mini", print_signatures: bool = False, 
                 reference_content: str = None):
        self.base_url = base_url
        self.model = model
        self.print_signatures = print_signatures
        self.prompt_generator = ZeekSignaturePromptGenerator(reference_content)
        self.dataset = []
        
    def generate_single_example(self) -> Dict[str, Any] or None:
        """Generate a single dataset example."""
        instruction, input_text, full_prompt = self.prompt_generator.generate_prompt()
        
        try:
            signature_output = self._query_llm_for_signature(full_prompt)
            
            if not signature_output:
                print(f"❌ No signature output received from LLM")
                return None
                
            is_valid, validation_message, processed_signature = self.prompt_generator.validate_signature_syntax(signature_output)
            if not is_valid:
                print(f"{validation_message}")
                if self.print_signatures:
                    print(f"   Complete generated content:")
                    print(f"   {'-' * 50}")
                    print(f"   {signature_output}")
                    print(f"   {'-' * 50}")
                    if processed_signature and processed_signature != signature_output:
                        print(f"   Processed content:")
                        print(f"   {'-' * 50}")
                        print(f"   {processed_signature}")
                        print(f"   {'-' * 50}")
                else:
                    print(f"   Generated content preview: {signature_output[:100]}...")
                return None
            
            # Use the processed signature for the final output
            final_signature = processed_signature if processed_signature else signature_output.strip()
            
            # Print complete signature if requested
            if self.print_signatures:
                print(f"📝 Generated Signature:")
                print(f"   Instruction: {instruction}")
                print(f"   Input: {input_text}")
                print(f"   {'-' * 60}")
                print(f"   {final_signature}")
                print(f"   {'-' * 60}")
                print()
            
            return {
                "instruction": instruction,
                "input": input_text,
                "output": final_signature
            }
            
        except Exception as e:
            print(f"Error generating example: {e}")
            return None
    
    def _query_llm_for_signature(self, prompt: str) -> str:
        """Query the LLM and return just the signature text."""
        import openai
        import time
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=self.base_url,
                timeout=1200000  # 20 minutes timeout
            )
            
            messages = [{"role": "user", "content": prompt}]
            full_reply = ""
            
            # Create streaming chat completion request
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            # Process the streaming response and collect only the content
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    part = chunk.choices[0].delta.content
                    full_reply += part
            
            return full_reply.strip()
            
        except openai.AuthenticationError as e:
            print(f"❌ Authentication Error: Invalid API key. Please check your OPENAI_API_KEY environment variable.")
            print(f"   Details: {e}")
            return ""
        except openai.RateLimitError as e:
            print(f"❌ Rate Limit Error: API rate limit exceeded. Please wait before retrying.")
            print(f"   Details: {e}")
            return ""
        except openai.APIConnectionError as e:
            print(f"❌ Connection Error: Unable to connect to the API endpoint.")
            print(f"   Base URL: {self.base_url}")
            print(f"   Details: {e}")
            return ""
        except openai.APITimeoutError as e:
            print(f"❌ Timeout Error: Request timed out after 20 minutes.")
            print(f"   Model: {self.model}")
            print(f"   Details: {e}")
            return ""
        except openai.BadRequestError as e:
            print(f"❌ Bad Request Error: Invalid request parameters.")
            print(f"   Model: {self.model}")
            print(f"   Base URL: {self.base_url}")
            print(f"   Details: {e}")
            return ""
        except Exception as e:
            print(f"❌ Unexpected Error: {type(e).__name__}")
            print(f"   Model: {self.model}")
            print(f"   Base URL: {self.base_url}")
            print(f"   Details: {e}")
            return ""
    
    def generate_dataset(self, count: int, output_file: str) -> None:
        """Generate the complete dataset."""
        print(f"Generating {count} Zeek signature examples...")
        
        successful = 0
        attempts = 0
        max_attempts = count * 3  # Allow up to 3x attempts for failures
        
        while successful < count and attempts < max_attempts:
            attempts += 1
            print(f"Generating example {successful + 1}/{count} (attempt {attempts})")
            
            example = self.generate_single_example()
            if example:
                self.dataset.append(example)
                successful += 1
                print(f"✓ Successfully generated example {successful}")
            else:
                print(f"✗ Failed to generate valid example")
        
        if successful < count:
            print(f"⚠️  Warning: Only generated {successful} valid examples out of {count} requested")
            print(f"   This may be due to API rate limits, validation failures, or connection issues")
        
        # Save dataset
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.dataset, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Dataset saved successfully to {output_file}")
            print(f"   Total examples: {len(self.dataset)}")
            print(f"   File size: {Path(output_file).stat().st_size} bytes")
            
        except PermissionError:
            print(f"❌ Permission Error: Cannot write to {output_file}")
            print(f"   Please check file permissions or choose a different output location")
        except json.JSONEncodeError as e:
            print(f"❌ JSON Encoding Error: Failed to serialize dataset")
            print(f"   Details: {e}")
            print(f"   Dataset contains {len(self.dataset)} examples")
        except Exception as e:
            print(f"❌ Unexpected Error saving dataset: {type(e).__name__}")
            print(f"   Output file: {output_file}")
            print(f"   Details: {e}")
            print(f"   Dataset contains {len(self.dataset)} examples")


def load_reference_document(file_path: str) -> str or None:
    """Load external reference document with error handling."""
    if not file_path:
        return None
    
    try:
        ref_path = Path(file_path)
        
        # Check if file exists
        if not ref_path.exists():
            print(f"⚠️  Warning: Reference document not found: {file_path}")
            return None
        
        # Check file size (limit to 50KB to prevent huge prompts)
        file_size = ref_path.stat().st_size
        max_size = 50 * 1024  # 50KB
        
        if file_size > max_size:
            print(f"⚠️  Warning: Reference document too large ({file_size} bytes > {max_size} bytes)")
            print(f"   File: {file_path}")
            print(f"   Consider splitting into smaller files or using key excerpts")
            return None
        
        # Load the file
        with open(ref_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print(f"⚠️  Warning: Reference document is empty: {file_path}")
            return None
        
        print(f"✓ Loaded reference document: {file_path} ({len(content)} chars)")
        return content
        
    except PermissionError:
        print(f"❌ Permission Error: Cannot read reference document {file_path}")
        return None
    except UnicodeDecodeError:
        print(f"❌ Encoding Error: Cannot decode reference document {file_path}")
        print(f"   Please ensure the file is in UTF-8 format")
        return None
    except Exception as e:
        print(f"❌ Error loading reference document: {type(e).__name__}")
        print(f"   File: {file_path}")
        print(f"   Details: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate Zeek signature dataset for LLM fine-tuning")
    parser.add_argument("--count", type=int, default=10, 
                       help="Number of signature examples to generate")
    parser.add_argument("--output", default="zeek_signatures_dataset.json",
                       help="Output JSON file for the dataset")
    parser.add_argument("--base_url", default="https://api.openai.com/v1",
                       help="Base URL of the OpenAI-compatible API")
    parser.add_argument("--model", default="gpt-4o-mini",
                       help="The model to use for generation")
    parser.add_argument("--print-signatures", action="store_true",
                       help="Print complete generated signatures to console during generation")
    parser.add_argument("--reference-doc", type=str, default=None,
                       help="Path to external text file containing reference examples, documentation, or signature patterns")
    
    args = parser.parse_args()
    
    # Validate that the LLM script exists (informational only)
    benchmark_dir = Path(__file__).parent.parent / "benchmark_models"
    llm_script = benchmark_dir / "stream_query_llm_long_prompt.py"
    
    if not llm_script.exists():
        print(f"⚠️  Warning: LLM reference script not found")
        print(f"   Expected location: {llm_script}")
        print(f"   This is not required - the dataset generator has its own LLM interface")
        print(f"   Continuing with dataset generation...")
    
    # Validate output directory exists
    output_path = Path(args.output)
    output_dir = output_path.parent
    
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created output directory: {output_dir}")
        except PermissionError:
            print(f"❌ Permission Error: Cannot create output directory {output_dir}")
            print(f"   Please check directory permissions or specify a different output path")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error creating output directory: {type(e).__name__}")
            print(f"   Directory: {output_dir}")
            print(f"   Details: {e}")
            sys.exit(1)
    
    # Load reference document if provided
    reference_content = load_reference_document(args.reference_doc)
    
    generator = ZeekDatasetGenerator(args.base_url, args.model, args.print_signatures, reference_content)
    generator.generate_dataset(args.count, args.output)


if __name__ == "__main__":
    main()