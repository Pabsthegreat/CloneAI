"""
Test document utility commands.
Compatible with both pytest and unittest.
"""

import unittest
import pytest
from agent.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestDocumentCommands(unittest.TestCase):
    """Test suite for document utility commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    
    def test_merge_pdf_help(self):
        """Test merge pdf command help."""
        result = self.runner.invoke(app, ["merge", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("pdf", result.stdout.lower())
        self.assertIn("ppt", result.stdout.lower())
    
    def test_merge_invalid_type(self):
        """Test merge with invalid document type."""
        result = self.runner.invoke(app, ["merge", "invalid"], input="\n")
        self.assertIn("Invalid document type", result.stdout)
    
    def test_convert_help(self):
        """Test convert command help."""
        result = self.runner.invoke(app, ["convert", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("pdf-to-docx", result.stdout.lower())
        self.assertIn("docx-to-pdf", result.stdout.lower())
        self.assertIn("ppt-to-pdf", result.stdout.lower())
    
    def test_convert_invalid_type(self):
        """Test convert with invalid conversion type."""
        result = self.runner.invoke(app, ["convert", "invalid-conversion"], input="\n")
        self.assertIn("Invalid conversion", result.stdout)
    
    def test_document_manager_list_files(self):
        """Test listing files in directory."""
        import tempfile
        from pathlib import Path
        from agent.tools.documents import DocumentManager
        
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_dir = Path(tmp_path)
            
            # Create test PDF files
            (tmp_dir / "test1.pdf").touch()
            (tmp_dir / "test2.pdf").touch()
            (tmp_dir / "test3.txt").touch()  # Not a PDF
            
            manager = DocumentManager()
            files = manager.list_files_in_directory(str(tmp_dir), 'pdf')
            
            # Should only list PDF files
            self.assertEqual(len(files), 2)
            filenames = [f[0] for f in files]
            self.assertIn("test1.pdf", filenames)
            self.assertIn("test2.pdf", filenames)
            self.assertNotIn("test3.txt", filenames)
    
    def test_document_manager_list_files_ppt(self):
        """Test listing PowerPoint files."""
        import tempfile
        from pathlib import Path
        from agent.tools.documents import DocumentManager
        
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_dir = Path(tmp_path)
            
            # Create test files
            (tmp_dir / "pres1.pptx").touch()
            (tmp_dir / "pres2.ppt").touch()
            (tmp_dir / "doc.pdf").touch()  # Not a PPT
            
            manager = DocumentManager()
            files = manager.list_files_in_directory(str(tmp_dir), 'ppt')
            
            self.assertEqual(len(files), 2)
            filenames = [f[0] for f in files]
            self.assertIn("pres1.pptx", filenames)
            self.assertIn("pres2.ppt", filenames)
            self.assertNotIn("doc.pdf", filenames)
    
    def test_document_manager_invalid_directory(self):
        """Test error handling for invalid directory."""
        from agent.tools.documents import DocumentManager
        
        manager = DocumentManager()
        
        with self.assertRaises(FileNotFoundError):
            manager.list_files_in_directory("/nonexistent/directory", 'pdf')
    
    def test_document_manager_invalid_file_type(self):
        """Test error handling for invalid file type."""
        from agent.tools.documents import DocumentManager
        import tempfile
        
        manager = DocumentManager()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "Unsupported file type"):
                manager.list_files_in_directory(tmp_dir, 'invalid')
    
    def test_merge_command_requires_directory(self):
        """Test that merge command prompts for directory."""
        result = self.runner.invoke(app, ["merge", "pdf"], input="\n")
        self.assertTrue("Enter directory path" in result.stdout or result.exit_code != 0)
    
    def test_convert_command_requires_input(self):
        """Test that convert command prompts for input file."""
        result = self.runner.invoke(app, ["convert", "pdf-to-docx"], input="\n")
        self.assertTrue("Enter input file path" in result.stdout or result.exit_code != 0)


# Pytest-style functions for compatibility
def test_merge_pdf_help():
    """Pytest wrapper for merge pdf command help test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_merge_pdf_help()


def test_merge_invalid_type():
    """Pytest wrapper for merge invalid type test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_merge_invalid_type()


def test_convert_help():
    """Pytest wrapper for convert help test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_convert_help()


def test_convert_invalid_type():
    """Pytest wrapper for convert invalid type test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_convert_invalid_type()


@pytest.fixture
def tmp_path_pytest(tmp_path):
    """Pytest fixture for temporary path."""
    return tmp_path


def test_document_manager_list_files(tmp_path_pytest):
    """Pytest wrapper using tmp_path fixture."""
    from pathlib import Path
    from agent.tools.documents import DocumentManager
    
    # Create test PDF files
    (tmp_path_pytest / "test1.pdf").touch()
    (tmp_path_pytest / "test2.pdf").touch()
    (tmp_path_pytest / "test3.txt").touch()  # Not a PDF
    
    manager = DocumentManager()
    files = manager.list_files_in_directory(str(tmp_path_pytest), 'pdf')
    
    # Should only list PDF files
    assert len(files) == 2
    filenames = [f[0] for f in files]
    assert "test1.pdf" in filenames
    assert "test2.pdf" in filenames
    assert "test3.txt" not in filenames


def test_document_manager_list_files_ppt(tmp_path_pytest):
    """Pytest wrapper using tmp_path fixture."""
    from agent.tools.documents import DocumentManager
    
    # Create test files
    (tmp_path_pytest / "pres1.pptx").touch()
    (tmp_path_pytest / "pres2.ppt").touch()
    (tmp_path_pytest / "doc.pdf").touch()  # Not a PPT
    
    manager = DocumentManager()
    files = manager.list_files_in_directory(str(tmp_path_pytest), 'ppt')
    
    assert len(files) == 2
    filenames = [f[0] for f in files]
    assert "pres1.pptx" in filenames
    assert "pres2.ppt" in filenames
    assert "doc.pdf" not in filenames


def test_document_manager_invalid_directory():
    """Pytest wrapper for invalid directory test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_document_manager_invalid_directory()


def test_document_manager_invalid_file_type():
    """Pytest wrapper for invalid file type test."""
    test = TestDocumentCommands()
    test.setUp()
    test.test_document_manager_invalid_file_type()


if __name__ == '__main__':
    unittest.main()
