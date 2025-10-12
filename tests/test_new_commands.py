"""
Test parsing for new mail:draft and calendar commands
"""
import re

def test_mail_draft_parsing():
    """Test mail:draft command parsing"""
    test_cases = [
        {
            "input": "mail:draft to:test@example.com subject:Meeting body:Let's meet tomorrow",
            "expected": {
                "to": "test@example.com",
                "subject": "Meeting",
                "body": "Let's meet tomorrow"
            }
        },
        {
            "input": "mail:draft to:user@test.com subject:Hello World body:This is a test cc:cc@test.com",
            "expected": {
                "to": "user@test.com",
                "subject": "Hello World",
                "body": "This is a test",
                "cc": "cc@test.com"
            }
        },
        {
            "input": "mail:draft to:abc@xyz.com subject:Report body:Please review bcc:manager@xyz.com",
            "expected": {
                "to": "abc@xyz.com",
                "subject": "Report",
                "body": "Please review",
                "bcc": "manager@xyz.com"
            }
        }
    ]
    
    print("\n" + "="*80)
    print("Testing mail:draft parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Extract parameters using regex (same as in cli.py)
        to_match = re.search(r'to:([^\s]+)', action, re.IGNORECASE)
        subject_match = re.search(r'subject:([^:]+?)(?:\s+(?:body|cc|bcc):|$)', action, re.IGNORECASE)
        body_match = re.search(r'body:(.+?)(?:\s+(?:cc|bcc):|$)', action, re.IGNORECASE)
        cc_match = re.search(r'cc:([^\s]+)', action, re.IGNORECASE)
        bcc_match = re.search(r'bcc:([^\s]+)', action, re.IGNORECASE)
        
        result = {
            "to": to_match.group(1) if to_match else None,
            "subject": subject_match.group(1).strip() if subject_match else None,
            "body": body_match.group(1).strip() if body_match else None,
        }
        if cc_match:
            result["cc"] = cc_match.group(1)
        if bcc_match:
            result["bcc"] = bcc_match.group(1)
        
        # Check if matches expected
        passed = all(result.get(k) == v for k, v in expected.items())
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")


def test_calendar_create_parsing():
    """Test calendar:create command parsing"""
    test_cases = [
        {
            "input": "calendar:create title:Team Meeting start:2025-10-15T14:00:00 duration:60",
            "expected": {
                "title": "Team Meeting",
                "start": "2025-10-15T14:00:00",
                "duration": 60
            }
        },
        {
            "input": "calendar:create title:Lunch start:2025-10-15T12:00:00 end:2025-10-15T13:00:00",
            "expected": {
                "title": "Lunch",
                "start": "2025-10-15T12:00:00",
                "end": "2025-10-15T13:00:00"
            }
        },
        {
            "input": "calendar:create title:Client Call start:2025-10-16T10:00:00 duration:30 location:Zoom",
            "expected": {
                "title": "Client Call",
                "start": "2025-10-16T10:00:00",
                "duration": 30,
                "location": "Zoom"
            }
        }
    ]
    
    print("\n" + "="*80)
    print("Testing calendar:create parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Extract parameters using regex (same as in cli.py)
        title_match = re.search(r'title:([^:]+?)(?=\s+(?:start|end|location|description|duration):|$)', action, re.IGNORECASE)
        start_match = re.search(r'start:([\d\-T:]+)(?=\s+|$)', action, re.IGNORECASE)
        end_match = re.search(r'end:([\d\-T:]+)(?=\s+|$)', action, re.IGNORECASE)
        duration_match = re.search(r'duration:(\d+)', action, re.IGNORECASE)
        location_match = re.search(r'location:([^\s]+?)(?=\s+(?:start|end|title|description|duration):|$)', action, re.IGNORECASE)
        
        result = {}
        if title_match:
            result["title"] = title_match.group(1).strip()
        if start_match:
            result["start"] = start_match.group(1).strip()
        if end_match:
            result["end"] = end_match.group(1).strip()
        if duration_match:
            result["duration"] = int(duration_match.group(1))
        if location_match:
            result["location"] = location_match.group(1).strip()
        
        # Check if matches expected
        passed = all(result.get(k) == v for k, v in expected.items())
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")


def test_calendar_list_parsing():
    """Test calendar:list command parsing"""
    test_cases = [
        {"input": "calendar:list next 5", "expected": 5},
        {"input": "calendar:list next 10", "expected": 10},
        {"input": "calendar:list", "expected": 10},  # default
    ]
    
    print("\n" + "="*80)
    print("Testing calendar:list parsing")
    print("="*80)
    
    for i, case in enumerate(test_cases, 1):
        action = case["input"]
        expected = case["expected"]
        
        # Parse "next N" pattern
        count = 10  # default
        count_match = re.search(r'(?:next|last)\s+(\d+)', action, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        
        passed = count == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"  Input: {action}")
        print(f"  Expected count: {expected}")
        print(f"  Got count: {count}")


if __name__ == "__main__":
    test_mail_draft_parsing()
    test_calendar_create_parsing()
    test_calendar_list_parsing()
    print("\n" + "="*80)
    print("All parsing tests completed!")
    print("="*80 + "\n")
