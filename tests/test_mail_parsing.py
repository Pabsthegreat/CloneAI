"""
Test script for mail command parsing
"""

import re

def test_mail_parsing():
    """Test the mail command parsing logic."""
    
    test_cases = [
        ("mail:list last 5", 5, None),
        ("mail:list last 10", 10, None),
        ("mail:list xyz@gmail.com", 5, "xyz@gmail.com"),
        ("mail:list john@example.com", 5, "john@example.com"),
        ("mail:list last 3 john@example.com", 3, "john@example.com"),
        ("mail:list john@example.com last 7", 7, "john@example.com"),
    ]
    
    print("Testing mail command parsing:\n")
    print("=" * 80)
    
    for action, expected_count, expected_sender in test_cases:
        count = 5  # default
        sender = None
        
        # Parse "last N" pattern
        last_match = re.search(r'last\s+(\d+)', action, re.IGNORECASE)
        if last_match:
            count = int(last_match.group(1))
        
        # Parse email address pattern
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', action)
        if email_match:
            sender = email_match.group(1)
        
        status = "✅" if count == expected_count and sender == expected_sender else "❌"
        
        print(f"\n{status} Input: '{action}'")
        print(f"   Expected: count={expected_count}, sender={expected_sender}")
        print(f"   Got:      count={count}, sender={sender}")
    
    print("\n" + "=" * 80)
    print("\nAll parsing tests complete!")

if __name__ == "__main__":
    test_mail_parsing()
