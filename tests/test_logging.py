"""
Test the command logging system
"""

from agent.state.logger import CommandLogger, get_logger
import os
import tempfile

def test_logging():
    """Test command logging with circular buffer."""
    
    # Create a temporary logger for testing
    temp_dir = tempfile.mkdtemp()
    temp_log = os.path.join(temp_dir, 'test_history.json')
    
    logger = CommandLogger(log_path=temp_log, max_entries=10)
    
    print("Testing Command Logging System")
    print("=" * 80)
    
    # Test 1: Add some commands
    print("\n1. Adding 5 commands...")
    for i in range(1, 6):
        logger.log_command(
            command=f"test command {i}",
            output=f"test output {i}",
            command_type="test",
            metadata={"index": i}
        )
    
    stats = logger.get_stats()
    print(f"   Total commands: {stats['total_commands']}")
    assert stats['total_commands'] == 5, "Should have 5 commands"
    print("   ✅ PASS")
    
    # Test 2: Add more than max_entries (10)
    print("\n2. Adding 10 more commands (total 15, max 10)...")
    for i in range(6, 16):
        logger.log_command(
            command=f"test command {i}",
            output=f"test output {i}",
            command_type="test",
            metadata={"index": i}
        )
    
    stats = logger.get_stats()
    print(f"   Total commands: {stats['total_commands']}")
    assert stats['total_commands'] == 10, "Should have exactly 10 commands (max)"
    print("   ✅ PASS - Circular buffer working!")
    
    # Test 3: Check oldest command is #6 (not #1)
    print("\n3. Checking circular buffer removed oldest entries...")
    history = logger.get_history(limit=100)
    oldest = history[-1]  # Last in reversed list is oldest
    print(f"   Oldest command: {oldest['command']}")
    assert "command 6" in oldest['command'], "Oldest should be command 6"
    print("   ✅ PASS - Old entries removed")
    
    # Test 4: Check newest command is #15
    print("\n4. Checking newest entry...")
    newest = history[0]  # First in reversed list is newest
    print(f"   Newest command: {newest['command']}")
    assert "command 15" in newest['command'], "Newest should be command 15"
    print("   ✅ PASS")
    
    # Test 5: Search functionality
    print("\n5. Testing search functionality...")
    results = logger.search_history("command 1")
    print(f"   Search 'command 1' found: {len(results)} results")
    # Should find command 10, 11, 12, 13, 14, 15 (all contain '1')
    assert len(results) >= 6, "Should find multiple results containing '1'"
    print("   ✅ PASS")
    
    # Test 6: Filter by command type
    print("\n6. Testing command type filter...")
    logger.log_command("mail command", "mail output", command_type="mail")
    mail_history = logger.get_history(command_type="mail")
    print(f"   Mail commands found: {len(mail_history)}")
    assert len(mail_history) == 1, "Should have 1 mail command"
    print("   ✅ PASS")
    
    # Test 7: Clear history
    print("\n7. Testing clear history...")
    logger.clear_history()
    stats = logger.get_stats()
    print(f"   Total commands after clear: {stats['total_commands']}")
    assert stats['total_commands'] == 0, "Should have 0 commands after clear"
    print("   ✅ PASS")
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("\nCircular buffer behavior verified:")
    print("  - Keeps last 100 commands (configurable)")
    print("  - Automatically removes oldest when limit reached")
    print("  - Search and filter working correctly")
    print("=" * 80)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_logging()
