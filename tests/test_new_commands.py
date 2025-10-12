import unittest
import re

class TestNewCommands(unittest.TestCase):
    def test_mail_draft_parsing(self):
        action = 'mail:draft to:test@example.com subject:Meeting body:Hello'
        to_match = re.search(r'to:([^\s]+)', action)
        self.assertIsNotNone(to_match)
        self.assertEqual(to_match.group(1), 'test@example.com')
    
    def test_calendar_create_parsing(self):
        action = 'calendar:create title:Meeting start:2025-10-15T14:00:00 duration:60'
        title_match = re.search(r'title:([^:]+?)(?=\s+(?:start|end):|$)', action)
        self.assertIsNotNone(title_match)
        self.assertEqual(title_match.group(1).strip(), 'Meeting')
    
    def test_calendar_list_parsing(self):
        action = 'calendar:list next 5'
        count_match = re.search(r'next\s+(\d+)', action)
        self.assertIsNotNone(count_match)
        self.assertEqual(int(count_match.group(1)), 5)

if __name__ == '__main__':
    unittest.main()
