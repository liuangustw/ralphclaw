#!/usr/bin/env python3
"""
Gemini API caller for ralph-claw

Usage:
  python3 call_gemini.py --role architect --key $API_KEY --input /path/to/prompt.txt
"""

import sys
import json
import os
import argparse
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed. Run: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)


def call_gemini(api_key: str, prompt: str, role: str = "general") -> str:
    """Call Gemini API and return response."""
    
    genai.configure(api_key=api_key)
    
    # Use appropriate model based on role
    model_name = "gemini-2.5-flash"  # Free tier supports this
    
    # System prompts for different roles
    system_prompts = {
        "architect": "You are an expert architect. Break down complex tasks into smaller, well-defined subtasks. Output MUST be valid JSON matching the CURRENT_TASK schema.",
        "builder": "You are an expert code builder. Generate minimal, focused code changes. Output the patch in APPLY_PATCH: ... format.",
        "replanner": "You are a task replanner. When a task fails, break it into smaller subtasks. Output MUST be valid JSON.",
        "verifier": "You are a code verifier. Analyze test results and failures. Output MUST be valid JSON.",
    }
    
    system_prompt = system_prompts.get(role, system_prompts["general"])
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8000,
            )
        )
        
        return response.text
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Call Gemini API for ralph-claw")
    parser.add_argument("--role", choices=["architect", "builder", "replanner", "verifier"], default="general")
    parser.add_argument("--key", required=True, help="Gemini API key")
    parser.add_argument("--input", required=True, help="Input file path (prompt)")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    # Read prompt from file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    prompt = input_path.read_text(encoding="utf-8")
    
    # Call Gemini
    print(f"[{args.role.upper()}] Calling Gemini API...", file=sys.stderr)
    response = call_gemini(args.key, prompt, args.role)
    
    # Output result
    if args.output:
        Path(args.output).write_text(response, encoding="utf-8")
        print(f"[{args.role.upper()}] Response written to {args.output}", file=sys.stderr)
    else:
        print(response)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
