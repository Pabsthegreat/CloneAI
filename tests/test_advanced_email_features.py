"""
Test suite for advanced email and calendar features.
Tests meeting detection, priority emails, scheduler, and cascading commands.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tools.email_parser import EmailParser, parse_email_for_meetings
from agent.tools.priority_emails import PriorityEmailManager, add_priority_sender, list_priority_senders
from agent.tools.scheduler import TaskScheduler, add_scheduled_task, list_scheduled_tasks


class TestEmailParser(unittest.TestCase):
    """Test email parsing for meeting detection."""
    
    def setUp(self):
        self.parser = EmailParser()
    
    def test_extract_google_meet_link(self):
        """Test Google Meet link detection."""
        text = "Join the meeting at https://meet.google.com/abc-defg-hij"
        links = self.parser.extract_meeting_links(text)
        
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['platform'], 'Google Meet')
        self.assertIn('meet.google.com', links[0]['url'])
    
    def test_extract_zoom_link(self):
        """Test Zoom link detection."""
        text = "Join Zoom Meeting: https://zoom.us/j/1234567890?pwd=abcdef123456"
        links = self.parser.extract_meeting_links(text)
        
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['platform'], 'Zoom')
        self.assertIn('zoom.us', links[0]['url'])
    
    def test_extract_teams_link(self):
        """Test Microsoft Teams link detection."""
        text = "Teams meeting: https://teams.microsoft.com/l/meetup-join/19%3ameeting_xyz"
        links = self.parser.extract_meeting_links(text)
        
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['platform'], 'Teams')
        self.assertIn('teams.microsoft.com', links[0]['url'])
    
    def test_extract_multiple_links(self):
        """Test multiple meeting link detection."""
        text = """
        Google Meet: https://meet.google.com/abc-defg-hij
        Zoom backup: https://zoom.us/j/1234567890
        """
        links = self.parser.extract_meeting_links(text)
        
        self.assertEqual(len(links), 2)
    
    def test_extract_iso_date(self):
        """Test ISO format date extraction."""
        text = "Meeting scheduled for 2025-10-15"
        dates = self.parser.extract_dates(text)
        
        self.assertGreater(len(dates), 0)
        self.assertIn('2025-10-15', dates[0])
    
    def test_extract_us_date(self):
        """Test US format date extraction."""
        text = "Meeting on 10/15/2025 at the office"
        dates = self.parser.extract_dates(text)
        
        self.assertGreater(len(dates), 0)
    
    def test_extract_natural_date(self):
        """Test natural language date extraction."""
        text = "Meeting on October 15, 2025"
        dates = self.parser.extract_dates(text)
        
        self.assertGreater(len(dates), 0)
        self.assertIn('October', dates[0])
    
    def test_extract_time_24hour(self):
        """Test 24-hour time format extraction."""
        text = "Meeting at 14:30 today"
        times = self.parser.extract_times(text)
        
        self.assertGreater(len(times), 0)
        self.assertIn('14:30', times[0])
    
    def test_extract_time_12hour(self):
        """Test 12-hour time format extraction."""
        text = "Meeting at 2:30 PM today"
        times = self.parser.extract_times(text)
        
        self.assertGreater(len(times), 0)
    
    def test_is_meeting_email_with_link(self):
        """Test meeting email detection with link."""
        subject = "Team Sync"
        body = "Join us at https://meet.google.com/abc-defg-hij"
        
        is_meeting = self.parser.is_meeting_email(subject, body)
        self.assertTrue(is_meeting)
    
    def test_is_meeting_email_with_keywords(self):
        """Test meeting email detection with keywords."""
        subject = "Meeting Invitation: Project Review"
        body = "Looking forward to our discussion tomorrow"
        
        is_meeting = self.parser.is_meeting_email(subject, body)
        self.assertTrue(is_meeting)
    
    def test_is_not_meeting_email(self):
        """Test non-meeting email detection."""
        subject = "Project Update"
        body = "Here's the latest status report"
        
        is_meeting = self.parser.is_meeting_email(subject, body)
        self.assertFalse(is_meeting)
    
    def test_extract_duration_minutes(self):
        """Test duration extraction in minutes."""
        text = "30 minute meeting"
        duration = self.parser.extract_duration(text)
        
        self.assertEqual(duration, 30)
    
    def test_extract_duration_hours(self):
        """Test duration extraction in hours."""
        text = "2 hour workshop"
        duration = self.parser.extract_duration(text)
        
        self.assertEqual(duration, 120)
    
    def test_extract_duration_mixed(self):
        """Test duration extraction in mixed format."""
        text = "Meeting will be 1h 30m"
        duration = self.parser.extract_duration(text)
        
        self.assertEqual(duration, 90)
    
    def test_extract_duration_default(self):
        """Test default duration when none specified."""
        text = "Regular meeting"
        duration = self.parser.extract_duration(text)
        
        self.assertEqual(duration, 60)  # Default
    
    def test_extract_meeting_info_complete(self):
        """Test complete meeting info extraction."""
        subject = "Team Standup"
        body = """
        Join us for our daily standup on October 15, 2025 at 10:00 AM.
        Google Meet link: https://meet.google.com/abc-defg-hij
        Duration: 30 minutes
        """
        
        info = self.parser.extract_meeting_info(subject, body)
        
        self.assertTrue(info['is_meeting'])
        self.assertGreater(len(info['meeting_links']), 0)
        self.assertGreater(len(info['dates']), 0)
        self.assertGreater(len(info['times']), 0)
    
    def test_parse_datetime_combination(self):
        """Test parsing date and time combination."""
        date_str = "2025-10-15"
        time_str = "14:30"
        
        dt = self.parser.parse_datetime(date_str, time_str)
        
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 15)


class TestPriorityEmailManager(unittest.TestCase):
    """Test priority email management."""
    
    def setUp(self):
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'priority_emails.json'
        
        # Patch the config path
        self.patcher = patch('agent.tools.priority_emails.get_priority_config_path')
        self.mock_config_path = self.patcher.start()
        self.mock_config_path.return_value = self.config_path
        
        self.manager = PriorityEmailManager()
    
    def tearDown(self):
        self.patcher.stop()
        # Cleanup temp files
        if self.config_path.exists():
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_add_priority_sender(self):
        """Test adding a priority sender."""
        self.manager.add_priority_sender('boss@company.com')
        
        self.assertIn('boss@company.com', self.manager.priority_senders)
    
    def test_add_priority_domain(self):
        """Test adding a priority domain."""
        self.manager.add_priority_domain('@company.com')
        
        self.assertIn('@company.com', self.manager.priority_domains)
    
    def test_add_priority_domain_without_at(self):
        """Test adding domain without @ symbol."""
        self.manager.add_priority_domain('company.com')
        
        self.assertIn('@company.com', self.manager.priority_domains)
    
    def test_remove_priority_sender(self):
        """Test removing a priority sender."""
        self.manager.add_priority_sender('boss@company.com')
        result = self.manager.remove_priority_sender('boss@company.com')
        
        self.assertTrue(result)
        self.assertNotIn('boss@company.com', self.manager.priority_senders)
    
    def test_remove_nonexistent_sender(self):
        """Test removing non-existent sender."""
        result = self.manager.remove_priority_sender('nobody@nowhere.com')
        
        self.assertFalse(result)
    
    def test_is_priority_email_exact_match(self):
        """Test exact email match."""
        self.manager.add_priority_sender('boss@company.com')
        
        self.assertTrue(self.manager.is_priority_email('boss@company.com'))
        self.assertFalse(self.manager.is_priority_email('other@company.com'))
    
    def test_is_priority_email_domain_match(self):
        """Test domain match."""
        self.manager.add_priority_domain('@company.com')
        
        self.assertTrue(self.manager.is_priority_email('anyone@company.com'))
        self.assertTrue(self.manager.is_priority_email('boss@company.com'))
        self.assertFalse(self.manager.is_priority_email('user@other.com'))
    
    def test_is_priority_email_with_name(self):
        """Test priority check with name in email."""
        self.manager.add_priority_sender('boss@company.com')
        
        # Email with name format
        self.assertTrue(self.manager.is_priority_email('Boss Name <boss@company.com>'))
    
    def test_filter_priority_emails(self):
        """Test filtering priority emails."""
        self.manager.add_priority_sender('boss@company.com')
        
        emails = [
            {'from': 'boss@company.com', 'subject': 'Important'},
            {'from': 'other@test.com', 'subject': 'Not important'},
            {'from': 'Boss <boss@company.com>', 'subject': 'Also important'}
        ]
        
        priority = self.manager.filter_priority_emails(emails)
        
        self.assertEqual(len(priority), 2)
    
    def test_persistence(self):
        """Test configuration persistence."""
        self.manager.add_priority_sender('boss@company.com')
        self.manager.add_priority_domain('@company.com')
        
        # Create new manager instance
        new_manager = PriorityEmailManager()
        
        self.assertIn('boss@company.com', new_manager.priority_senders)
        self.assertIn('@company.com', new_manager.priority_domains)
    
    def test_get_priority_list(self):
        """Test getting priority configuration."""
        self.manager.add_priority_sender('boss@company.com')
        self.manager.add_priority_domain('@company.com')
        
        config = self.manager.get_priority_list()
        
        self.assertEqual(config['total'], 2)
        self.assertIn('boss@company.com', config['senders'])
        self.assertIn('@company.com', config['domains'])


class TestTaskScheduler(unittest.TestCase):
    """Test task scheduler."""
    
    def setUp(self):
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'scheduler_config.json'
        self.log_path = Path(self.temp_dir) / 'scheduler.log'
        
        # Patch the paths
        self.patcher1 = patch('agent.tools.scheduler.get_scheduler_config_path')
        self.patcher2 = patch('agent.tools.scheduler.get_scheduler_log_path')
        
        self.mock_config_path = self.patcher1.start()
        self.mock_log_path = self.patcher2.start()
        
        self.mock_config_path.return_value = self.config_path
        self.mock_log_path.return_value = self.log_path
        
        self.scheduler = TaskScheduler()
    
    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        
        # Cleanup temp files
        if self.config_path.exists():
            os.remove(self.config_path)
        if self.log_path.exists():
            os.remove(self.log_path)
        os.rmdir(self.temp_dir)
    
    def test_add_task(self):
        """Test adding a scheduled task."""
        task = self.scheduler.add_task(
            name="Morning Email Check",
            command="mail:list",
            time="09:00"
        )
        
        self.assertEqual(task['name'], "Morning Email Check")
        self.assertEqual(task['command'], "mail:list")
        self.assertEqual(task['time'], "09:00")
        self.assertTrue(task['enabled'])
    
    def test_remove_task(self):
        """Test removing a task."""
        task = self.scheduler.add_task("Test", "mail:list", "09:00")
        task_id = task['id']
        
        result = self.scheduler.remove_task(task_id)
        
        self.assertTrue(result)
        self.assertEqual(len(self.scheduler.tasks), 0)
    
    def test_remove_nonexistent_task(self):
        """Test removing non-existent task."""
        result = self.scheduler.remove_task(999)
        
        self.assertFalse(result)
    
    def test_toggle_task(self):
        """Test enabling/disabling a task."""
        task = self.scheduler.add_task("Test", "mail:list", "09:00")
        task_id = task['id']
        
        # Toggle to disabled
        updated = self.scheduler.toggle_task(task_id)
        self.assertFalse(updated['enabled'])
        
        # Toggle back to enabled
        updated = self.scheduler.toggle_task(task_id)
        self.assertTrue(updated['enabled'])
    
    def test_get_tasks_all(self):
        """Test getting all tasks."""
        self.scheduler.add_task("Task 1", "mail:list", "09:00")
        self.scheduler.add_task("Task 2", "calendar:list", "10:00")
        
        tasks = self.scheduler.get_tasks()
        
        self.assertEqual(len(tasks), 2)
    
    def test_get_tasks_enabled_only(self):
        """Test getting only enabled tasks."""
        task1 = self.scheduler.add_task("Task 1", "mail:list", "09:00")
        task2 = self.scheduler.add_task("Task 2", "calendar:list", "10:00")
        
        # Disable task 2
        self.scheduler.toggle_task(task2['id'])
        
        enabled_tasks = self.scheduler.get_tasks(enabled_only=True)
        
        self.assertEqual(len(enabled_tasks), 1)
        self.assertEqual(enabled_tasks[0]['name'], "Task 1")
    
    def test_update_task_status(self):
        """Test updating task execution status."""
        task = self.scheduler.add_task("Test", "mail:list", "09:00")
        task_id = task['id']
        
        self.scheduler.update_task_status(task_id, "success")
        
        # Reload tasks
        self.scheduler.load_tasks()
        updated_task = [t for t in self.scheduler.tasks if t['id'] == task_id][0]
        
        self.assertEqual(updated_task['last_status'], "success")
        self.assertIsNotNone(updated_task['last_run'])
    
    def test_persistence(self):
        """Test task persistence."""
        self.scheduler.add_task("Task 1", "mail:list", "09:00")
        self.scheduler.add_task("Task 2", "calendar:list", "10:00")
        
        # Create new scheduler instance
        new_scheduler = TaskScheduler()
        
        self.assertEqual(len(new_scheduler.tasks), 2)
    
    def test_log_execution(self):
        """Test execution logging."""
        task = self.scheduler.add_task("Test", "mail:list", "09:00")
        
        self.scheduler.log_execution(task['id'], "Test execution")
        
        self.assertTrue(self.log_path.exists())
        
        with open(self.log_path, 'r') as f:
            content = f.read()
            self.assertIn("Test execution", content)


class TestCascadingCommands(unittest.TestCase):
    """Test cascading command execution."""
    
    def test_split_cascading_commands(self):
        """Test splitting commands on &&."""
        action = "mail:list && calendar:list && tasks"
        commands = [cmd.strip() for cmd in action.split('&&')]
        
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0], "mail:list")
        self.assertEqual(commands[1], "calendar:list")
        self.assertEqual(commands[2], "tasks")
    
    def test_single_command_no_cascade(self):
        """Test single command (no &&)."""
        action = "mail:list last 10"
        
        self.assertNotIn('&&', action)


class TestIntegration(unittest.TestCase):
    """Integration tests for combined features."""
    
    def test_meeting_workflow(self):
        """Test complete meeting detection workflow."""
        parser = EmailParser()
        
        # Simulate email with meeting
        subject = "Team Standup - Tomorrow"
        body = """
        Hi team,
        
        Let's have our daily standup tomorrow, October 15, 2025 at 10:00 AM.
        
        Join here: https://meet.google.com/abc-defg-hij
        
        Duration: 30 minutes
        
        Thanks!
        """
        
        # Extract meeting info
        info = parser.extract_meeting_info(subject, body)
        
        self.assertTrue(info['is_meeting'])
        self.assertEqual(len(info['meeting_links']), 1)
        self.assertIn('meet.google.com', info['meeting_links'][0]['url'])
        
        # Check duration extraction
        duration = parser.extract_duration(body)
        self.assertEqual(duration, 30)
    
    def test_priority_and_scheduler_workflow(self):
        """Test priority emails with scheduled tasks."""
        # Setup temporary directories
        temp_dir = tempfile.mkdtemp()
        priority_config = Path(temp_dir) / 'priority.json'
        scheduler_config = Path(temp_dir) / 'scheduler.json'
        scheduler_log = Path(temp_dir) / 'scheduler.log'
        
        try:
            # Patch paths
            with patch('agent.tools.priority_emails.get_priority_config_path', return_value=priority_config), \
                 patch('agent.tools.scheduler.get_scheduler_config_path', return_value=scheduler_config), \
                 patch('agent.tools.scheduler.get_scheduler_log_path', return_value=scheduler_log):
                
                # Add priority sender
                priority_mgr = PriorityEmailManager()
                priority_mgr.add_priority_sender('boss@company.com')
                
                # Add scheduled task to check priority emails
                scheduler = TaskScheduler()
                task = scheduler.add_task(
                    name="Check Priority Emails",
                    command="mail:priority last 10",
                    time="09:00"
                )
                
                # Verify
                self.assertIn('boss@company.com', priority_mgr.priority_senders)
                self.assertEqual(len(scheduler.tasks), 1)
                self.assertEqual(scheduler.tasks[0]['command'], "mail:priority last 10")
        
        finally:
            # Cleanup
            for f in [priority_config, scheduler_config, scheduler_log]:
                if f.exists():
                    os.remove(f)
            os.rmdir(temp_dir)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEmailParser))
    suite.addTests(loader.loadTestsFromTestCase(TestPriorityEmailManager))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestCascadingCommands))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
