"""
Test script for mail command parsing.
Compatible with both pytest and unittest.
"""

import unittest
import re


class TestMailParsing(unittest.TestCase):
    """Test suite for mail command parsing."""
    
    def test_mail_parsing(self):
        """Test the mail command parsing logic."""
        
        test_cases = [
            ("mail:list last 5", 5, None),
            ("mail:list last 10", 10, None),
            ("mail:list xyz@gmail.com", 5, "xyz@gmail.com"),
            ("mail:list john@example.com", 5, "john@example.com"),
            ("mail:list last 3 john@example.com", 3, "john@example.com"),
            ("mail:list john@example.com last 7", 7, "john@example.com"),
        ]
        
        for action, expected_count, expected_sender in test_cases:
            with self.subTest(action=action):
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
                
                self.assertEqual(count, expected_count,
                               f"Count mismatch for '{action}': expected {expected_count}, got {count}")
                self.assertEqual(sender, expected_sender,
                               f"Sender mismatch for '{action}': expected {expected_sender}, got {sender}")


# Pytest-style function for compatibility
def test_mail_parsing():
    """Pytest wrapper for mail parsing test."""
    test = TestMailParsing()
    test.test_mail_parsing()


if __name__ == "__main__":
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMailParsing)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*80)
