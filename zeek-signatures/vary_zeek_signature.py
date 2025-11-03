#!/usr/bin/env python3
"""
Zeek Signature Variation Generator

This script takes an existing Zeek signature as input and generates N variations with modified 
regex patterns that match more or less strictly. It uses LLM to create diverse signature 
variations while maintaining the original detection intent.

Usage:
    # Generate broader variations from file
    python3 vary_zeek_signature.py --input signature.sig --count 5 --strategy broader
    
    # Generate stricter variations from direct input
    python3 vary_zeek_signature.py --signature "signature test { payload /root/; event 'test'; }" --count 3 --strategy stricter
    
    # Mixed variations with custom model
    python3 vary_zeek_signature.py --input sig.sig --count 10 --strategy mixed --model gpt-4o
    
    # Output to file
    python3 vary_zeek_signature.py --input sig.sig --count 5 --output variations.json
"""

import json
import re
import argparse
import os
import sys
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# Add the benchmark_models directory to the path to import the LLM query script
benchmark_dir = Path(__file__).parent.parent / "benchmark_models"
sys.path.append(str(benchmark_dir))


class ZeekSignatureParser:
    """Parses Zeek signatures and extracts modifiable components."""
    
    def __init__(self):
        self.signature_pattern = re.compile(
            r'signature\s+([\w-]+)\s*\{([^}]+)\}', 
            re.MULTILINE | re.DOTALL
        )
        self.component_patterns = {
            'ip-proto': re.compile(r'ip-proto\s*==\s*(\w+)'),
            'src-ip': re.compile(r'src-ip\s*==\s*([^\n]+)'),
            'dst-ip': re.compile(r'dst-ip\s*==\s*([^\n]+)'),
            'src-port': re.compile(r'src-port\s*==\s*([^\n]+)'),
            'dst-port': re.compile(r'dst-port\s*==\s*([^\n]+)'),
            'payload': re.compile(r'payload\s+/([^/]+)/([gimsx]*)'),
            'http-request': re.compile(r'http-request\s+/([^/]+)/([gimsx]*)'),
            'http-reply': re.compile(r'http-reply\s+/([^/]+)/([gimsx]*)'),
            'event': re.compile(r'event\s+"([^"]+)"'),
            'tcp-state': re.compile(r'tcp-state\s+([^\n]+)'),
        }
    
    def parse_signature(self, signature: str) -> Dict[str, Any]:
        """Parse a Zeek signature and extract its components."""
        signature = signature.strip()
        
        # Match the overall signature structure
        match = self.signature_pattern.search(signature)
        if not match:
            raise ValueError("Invalid Zeek signature format")
        
        name = match.group(1)
        body = match.group(2).strip()
        
        # Extract individual components
        components = {
            'name': name,
            'original': signature,
            'body': body,
            'modifiable_patterns': []
        }
        
        # Parse each component type
        for component_type, pattern in self.component_patterns.items():
            matches = pattern.findall(body)
            if matches:
                components[component_type] = matches
                # Mark regex patterns as modifiable
                if component_type in ['payload', 'http-request', 'http-reply']:
                    for match in matches:
                        if isinstance(match, tuple):
                            regex_pattern, flags = match
                        else:
                            regex_pattern, flags = match, ''
                        components['modifiable_patterns'].append({
                            'type': component_type,
                            'pattern': regex_pattern,
                            'flags': flags
                        })
        
        return components
    
    def validate_signature_syntax(self, signature: str) -> Tuple[bool, str]:
        """Validate basic Zeek signature syntax."""
        if not signature.strip():
            return False, "Empty signature"
        
        # Check for basic signature structure
        if not signature.strip().startswith('signature'):
            return False, "Signature must start with 'signature' keyword"
        
        if '{' not in signature or '}' not in signature:
            return False, "Missing braces in signature"
        
        # Check brace balance
        open_braces = signature.count('{')
        close_braces = signature.count('}')
        if open_braces != close_braces:
            return False, f"Unbalanced braces: {open_braces} opening, {close_braces} closing"
        
        # Try to parse with our parser
        try:
            self.parse_signature(signature)
            return True, "Valid signature syntax"
        except ValueError as e:
            return False, f"Parse error: {e}"


class SignatureVariationGenerator:
    """Generates variations of Zeek signatures using LLM."""
    
    def __init__(self, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self.base_url = base_url
        self.model = model
        self.parser = ZeekSignatureParser()
    
    def create_variation_prompt(self, signature: str, strategy: str, count: int) -> str:
        """Create a prompt for generating signature variations."""
        strategy_descriptions = {
            'broader': {
                'description': 'BROADER matching patterns (less specific, matches more cases)',
                'examples': [
                    '/root/ → /r.{0,2}t/ (allows character variations)',
                    '/malware/ → /.*mal.*ware.*/ (allows separating characters)',
                    '/GET / → /GET.*/ (less specific path matching)',
                    '/admin/ → /[aA][dD][mM][iI][nN]/ (case variations)'
                ]
            },
            'stricter': {
                'description': 'STRICTER matching patterns (more specific, matches fewer cases)',
                'examples': [
                    '/root/ → /\\broot\\b/ (word boundaries)',
                    '/GET.*/ → /^GET \\/specific\\/path/ (exact path matching)',
                    '/admin/ → /admin(?=\\s|$)/ (require word end)',
                    '/.exe/ → /\\.exe$/ (exact file extension at end)'
                ]
            },
            'mixed': {
                'description': 'MIXED variations (some broader, some stricter)',
                'examples': [
                    'Mix of the above strategies',
                    'Generate roughly half broader, half stricter patterns'
                ]
            }
        }
        
        strategy_info = strategy_descriptions.get(strategy, strategy_descriptions['mixed'])
        
        prompt = f"""Given this Zeek signature:
{signature}

Generate {count} variations of this signature with {strategy_info['description']}.

{strategy} examples:
{chr(10).join(f'- {ex}' for ex in strategy_info['examples'])}

Rules:
1. Maintain valid Zeek signature syntax
2. Keep the same detection intent and threat context
3. Only modify payload/http-request/http-reply regex patterns
4. Each signature must be complete and syntactically correct
5. Give each variation a unique name (add suffix like -v1, -v2, etc.)
6. Output each signature on a separate line with no extra formatting

Examples of modifications to make patterns {strategy}:
- Broader: Add wildcards, make case-insensitive, allow character variations
- Stricter: Add anchors, word boundaries, exact matches, escape special chars

Output only the raw Zeek signatures, one per line:"""

        return prompt
    
    def generate_variations(self, signature: str, strategy: str = 'mixed', count: int = 5) -> List[Dict[str, Any]]:
        """Generate signature variations using LLM."""
        print(f"🔄 Generating {count} {strategy} variations...")
        
        # Parse original signature to understand structure
        try:
            parsed = self.parser.parse_signature(signature)
            print(f"✓ Parsed signature '{parsed['name']}' with {len(parsed['modifiable_patterns'])} modifiable patterns")
        except ValueError as e:
            print(f"❌ Failed to parse input signature: {e}")
            return []
        
        # Generate variations using LLM
        prompt = self.create_variation_prompt(signature, strategy, count)
        
        try:
            variations_text = self._query_llm(prompt)
            if not variations_text:
                print("❌ No variations generated by LLM")
                return []
            
            # Process LLM output into individual signatures
            variations = self._process_llm_output(variations_text, strategy)
            
            print(f"✓ Generated {len(variations)} valid variations out of {count} requested")
            return variations
            
        except Exception as e:
            print(f"❌ Error generating variations: {e}")
            return []
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM and return response text."""
        import openai
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        try:
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=self.base_url,
                timeout=1200  # 20 minutes timeout
            )
            
            messages = [{"role": "user", "content": prompt}]
            full_reply = ""
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    part = chunk.choices[0].delta.content
                    full_reply += part
            
            return full_reply.strip()
            
        except Exception as e:
            print(f"❌ LLM Query Error: {e}")
            return ""
    
    def _process_llm_output(self, output: str, strategy: str) -> List[Dict[str, Any]]:
        """Process LLM output into validated signature variations."""
        variations = []
        
        # Split output into individual signatures
        lines = output.strip().split('\n')
        current_signature = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('signature '):
                # Start of new signature
                if current_signature:
                    # Process previous signature
                    variation = self._validate_and_create_variation(current_signature, strategy, len(variations) + 1)
                    if variation:
                        variations.append(variation)
                current_signature = line
            else:
                # Continuation of current signature
                current_signature += f"\n{line}"
        
        # Process last signature
        if current_signature:
            variation = self._validate_and_create_variation(current_signature, strategy, len(variations) + 1)
            if variation:
                variations.append(variation)
        
        return variations
    
    def _validate_and_create_variation(self, signature: str, strategy: str, index: int) -> Optional[Dict[str, Any]]:
        """Validate a signature and create variation metadata."""
        is_valid, message = self.parser.validate_signature_syntax(signature)
        
        if not is_valid:
            print(f"⚠️  Variation {index} invalid: {message}")
            return None
        
        try:
            parsed = self.parser.parse_signature(signature)
            return {
                'signature': signature.strip(),
                'name': parsed['name'],
                'strategy': strategy,
                'index': index,
                'modifiable_patterns': parsed['modifiable_patterns'],
                'valid': True
            }
        except Exception as e:
            print(f"⚠️  Variation {index} parse error: {e}")
            return None


def load_signature_from_file(file_path: str) -> str:
    """Load signature from file with error handling."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Signature file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            raise ValueError(f"Signature file is empty: {file_path}")
        
        print(f"✓ Loaded signature from {file_path} ({len(content)} characters)")
        return content
        
    except Exception as e:
        print(f"❌ Error loading signature file: {e}")
        raise


def save_variations(variations: List[Dict[str, Any]], output_path: str, format_type: str = 'json'):
    """Save variations to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(variations, f, indent=2, ensure_ascii=False)
        elif format_type == 'sig':
            with open(output_file, 'w', encoding='utf-8') as f:
                for var in variations:
                    f.write(var['signature'])
                    f.write('\n\n')
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"✅ Saved {len(variations)} variations to {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving variations: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate variations of Zeek signatures using LLM")
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i", help="Path to Zeek signature file")
    input_group.add_argument("--signature", "-s", help="Direct signature string")
    
    # Generation options
    parser.add_argument("--count", "-c", type=int, default=5, 
                       help="Number of variations to generate (default: 5)")
    parser.add_argument("--strategy", choices=['broader', 'stricter', 'mixed'], default='mixed',
                       help="Variation strategy (default: mixed)")
    
    # Output options
    parser.add_argument("--output", "-o", help="Output file path (default: print to console)")
    parser.add_argument("--format", choices=['json', 'sig'], default='json',
                       help="Output format (default: json)")
    
    # LLM options
    parser.add_argument("--base_url", default="https://api.openai.com/v1",
                       help="Base URL of the OpenAI-compatible API")
    parser.add_argument("--model", default="gpt-4o-mini",
                       help="The model to use for generation")
    
    # Debug options
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load input signature
    try:
        if args.input:
            signature = load_signature_from_file(args.input)
        else:
            signature = args.signature.strip()
        
        if not signature:
            print("❌ Empty signature input")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to load signature: {e}")
        sys.exit(1)
    
    # Generate variations
    generator = SignatureVariationGenerator(args.base_url, args.model)
    variations = generator.generate_variations(signature, args.strategy, args.count)
    
    if not variations:
        print("❌ No valid variations generated")
        sys.exit(1)
    
    # Output results
    if args.output:
        save_variations(variations, args.output, args.format)
    else:
        print(f"\n🎯 Generated {len(variations)} {args.strategy} variations:\n")
        for i, var in enumerate(variations, 1):
            print(f"--- Variation {i}: {var['name']} ---")
            print(var['signature'])
            print()


if __name__ == "__main__":
    main()