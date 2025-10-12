"""
Test parsing for extended email commands (drafts, send, attachments)
"""
import re

def test_mail_drafts_parsing():
    """Test mail:drafts command parsing"""
    test_cases = [
        {"input": "mail:drafts", "expected": 10},
        {"input": "mail:drafts last 5", "expected": 5},
        {"input": "mail:drafts last 20", "expected": 20},
    ]
    
    print("\n" + "="*80)
    print("Testing mail:drafts parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Parse "last N" pattern
        count = 10  # default
        count_match = re.search(r'(?:last|next)\s+(\d+)', action, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        
        passed = count == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected count: {expected}")
        print(f"  Got count: {count}")


def test_mail_send_parsing():
    """Test mail:send command parsing"""
    test_cases = [
        {
            "input": "mail:send to:test@example.com subject:Hello body:Hi there",
            "expected": {
                "to": "test@example.com",
                "subject": "Hello",
                "body": "Hi there",
                "attachments": None
            }
        },
        {
            "input": "mail:send to:user@test.com subject:Document body:Please review attachments:C:\\file.pdf,C:\\doc.docx",
            "expected": {
                "to": "user@test.com",
                "subject": "Document",
                "body": "Please review",
                "attachments": ["C:\\file.pdf", "C:\\doc.docx"]
            }
        },
        {
            "input": "mail:send to:team@work.com subject:Report body:See attached cc:boss@work.com attachments:C:\\report.pdf",
            "expected": {
                "to": "team@work.com",
                "subject": "Report",
                "body": "See attached",
                "cc": "boss@work.com",
                "attachments": ["C:\\report.pdf"]
            }
        }
    ]
    
    print("\n" + "="*80)
    print("Testing mail:send parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Extract parameters using regex
        to_match = re.search(r'to:([^\s]+)', action, re.IGNORECASE)
        subject_match = re.search(r'subject:([^:]+?)(?:\s+(?:body|cc|bcc|attachments):|$)', action, re.IGNORECASE)
        body_match = re.search(r'body:(.+?)(?:\s+(?:cc|bcc|attachments):|$)', action, re.IGNORECASE)
        cc_match = re.search(r'cc:([^\s]+)', action, re.IGNORECASE)
        bcc_match = re.search(r'bcc:([^\s]+)', action, re.IGNORECASE)
        attachments_match = re.search(r'attachments:(.+?)(?:\s+(?:cc|bcc):|$)', action, re.IGNORECASE)
        
        result = {
            "to": to_match.group(1) if to_match else None,
            "subject": subject_match.group(1).strip() if subject_match else None,
            "body": body_match.group(1).strip() if body_match else None,
        }
        if cc_match:
            result["cc"] = cc_match.group(1)
        if bcc_match:
            result["bcc"] = bcc_match.group(1)
        if attachments_match:
            result["attachments"] = [path.strip() for path in attachments_match.group(1).split(',')]
        else:
            result["attachments"] = None
        
        # Check if matches expected
        passed = all(result.get(k) == v for k, v in expected.items())
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")


def test_mail_send_draft_parsing():
    """Test mail:send draft-id command parsing"""
    test_cases = [
        {"input": "mail:send draft-id:r123456789", "expected": "r123456789"},
        {"input": "mail:send draft-id:r-987654321", "expected": "r-987654321"},
        {"input": "mail:send draft-id:abc123def456", "expected": "abc123def456"},
    ]
    
    print("\n" + "="*80)
    print("Testing mail:send draft-id parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Extract draft ID
        draft_id_match = re.search(r'draft-id:([^\s]+)', action, re.IGNORECASE)
        
        result = draft_id_match.group(1) if draft_id_match else None
        passed = result == expected
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected draft_id: {expected}")
        print(f"  Got draft_id: {result}")


if __name__ == "__main__":
    test_mail_drafts_parsing()
    test_mail_send_parsing()
    test_mail_send_draft_parsing()
    print("\n" + "="*80)
    print("All email command parsing tests completed!")
    print("="*80 + "\n")
