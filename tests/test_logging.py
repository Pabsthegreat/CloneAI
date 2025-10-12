"""
Test the command logging system.
Compatible with both pytest and unittest.
"""

import unittest
import os
import tempfile
from agent.state.logger import CommandLogger, get_logger


class TestCommandLogging(unittest.TestCase):
    """Test suite for command logging system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_log = os.path.join(self.temp_dir, 'test_history.json')
        self.logger = CommandLogger(log_path=self.temp_log, max_entries=10)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_logging(self):
        """Test command logging with circular buffer."""
        # Test 1: Add some commands
        for i in range(1, 6):
            self.logger.log_command(
                command=f"test command {i}",
                output=f"test output {i}",
                command_type="test",
                metadata={"index": i}
            )
        
        stats = self.logger.get_stats()
        self.assertEqual(stats['total_commands'], 5, "Should have 5 commands")
        
        # Test 2: Add more than max_entries (10)
        for i in range(6, 16):
            self.logger.log_command(
                command=f"test command {i}",
                output=f"test output {i}",
                command_type="test",
                metadata={"index": i}
            )
        
        stats = self.logger.get_stats()
        self.assertEqual(stats['total_commands'], 10, "Should have exactly 10 commands (max)")
        
        # Test 3: Check oldest command is #6 (not #1)
        history = self.logger.get_history(limit=100)
        oldest = history[-1]  # Last in reversed list is oldest
        self.assertIn("command 6", oldest['command'], "Oldest should be command 6")
        
        # Test 4: Check newest command is #15
        newest = history[0]  # First in reversed list is newest
        self.assertIn("command 15", newest['command'], "Newest should be command 15")
        
        # Test 5: Search functionality
        results = self.logger.search_history("command 1")
        # Should find command 10, 11, 12, 13, 14, 15 (all contain '1')
        self.assertGreaterEqual(len(results), 6, "Should find multiple results containing '1'")
        
        # Test 6: Filter by command type
        self.logger.log_command("mail command", "mail output", command_type="mail")
        mail_history = self.logger.get_history(command_type="mail")
        self.assertEqual(len(mail_history), 1, "Should have 1 mail command")
        
        # Test 7: Clear history
        self.logger.clear_history()
        stats = self.logger.get_stats()
        self.assertEqual(stats['total_commands'], 0, "Should have 0 commands after clear")


# Pytest-style function for compatibility
def test_logging():
    """Pytest wrapper for logging test."""
    test = TestCommandLogging()
    test.setUp()
    try:
        test.test_logging()
    finally:
        test.tearDown()


if __name__ == "__main__":
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCommandLogging)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*80)
