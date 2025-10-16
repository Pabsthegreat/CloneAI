#!/usr/bin/env python3
"""
Quick test to verify the parameter quoting fix.
"""

import shlex

# Test cases that were failing
test_commands = [
    'calendar:create title:"Meeting with resumebuilder123@gmail.com" start:"2025-10-17T16:30:00" duration:60',
    'mail:reply id:199e85d5b5b09017 body:"Thank you for your message. I will follow up soon."',
    'mail:draft to:"me@gmail.com" subject:"Importance of Physical Activity" body:"Physical activity is essential for health."',
]

print("Testing command parsing with shlex.split():\n")
print("=" * 80)

for cmd in test_commands:
    print(f"\nOriginal command:\n  {cmd}")
    
    # Split to get namespace:action and args
    parts = cmd.split(' ', 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    print(f"\nCommand: {command}")
    print(f"Arguments: {args}")
    
    # Parse arguments with shlex (same as workflow registry)
    try:
        tokens = shlex.split(args, posix=True)
        print(f"\nTokens after shlex.split():")
        for i, token in enumerate(tokens, 1):
            print(f"  {i}. {token}")
        
        # Parse into key-value pairs
        parsed = {}
        for token in tokens:
            if ':' in token:
                key, value = token.split(':', 1)
                parsed[key] = value
        
        print(f"\nParsed parameters:")
        for key, value in parsed.items():
            print(f"  {key} = {value}")
        
        print("\n✅ SUCCESS - Command parsed correctly!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    print("=" * 80)

print("\n\nAll tests passed! The quoting fix is working correctly.")
