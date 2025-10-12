"""
Test document utility commands.
"""

import pytest
from agent.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_merge_pdf_help():
    """Test merge pdf command help."""
    result = runner.invoke(app, ["merge", "--help"])
    assert result.exit_code == 0
    assert "pdf" in result.stdout.lower()
    assert "ppt" in result.stdout.lower()


def test_merge_invalid_type():
    """Test merge with invalid document type."""
    result = runner.invoke(app, ["merge", "invalid"], input="\n")
    assert "Invalid document type" in result.stdout


def test_convert_help():
    """Test convert command help."""
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    assert "pdf-to-docx" in result.stdout.lower()
    assert "docx-to-pdf" in result.stdout.lower()
    assert "ppt-to-pdf" in result.stdout.lower()


def test_convert_invalid_type():
    """Test convert with invalid conversion type."""
    result = runner.invoke(app, ["convert", "invalid-conversion"], input="\n")
    assert "Invalid conversion" in result.stdout


def test_document_manager_list_files(tmp_path):
    """Test listing files in directory."""
    from agent.tools.documents import DocumentManager
    
    # Create test PDF files
    (tmp_path / "test1.pdf").touch()
    (tmp_path / "test2.pdf").touch()
    (tmp_path / "test3.txt").touch()  # Not a PDF
    
    manager = DocumentManager()
    files = manager.list_files_in_directory(str(tmp_path), 'pdf')
    
    # Should only list PDF files
    assert len(files) == 2
    filenames = [f[0] for f in files]
    assert "test1.pdf" in filenames
    assert "test2.pdf" in filenames
    assert "test3.txt" not in filenames


def test_document_manager_list_files_ppt(tmp_path):
    """Test listing PowerPoint files."""
    from agent.tools.documents import DocumentManager
    
    # Create test files
    (tmp_path / "pres1.pptx").touch()
    (tmp_path / "pres2.ppt").touch()
    (tmp_path / "doc.pdf").touch()  # Not a PPT
    
    manager = DocumentManager()
    files = manager.list_files_in_directory(str(tmp_path), 'ppt')
    
    assert len(files) == 2
    filenames = [f[0] for f in files]
    assert "pres1.pptx" in filenames
    assert "pres2.ppt" in filenames
    assert "doc.pdf" not in filenames


def test_document_manager_invalid_directory():
    """Test error handling for invalid directory."""
    from agent.tools.documents import DocumentManager
    
    manager = DocumentManager()
    
    with pytest.raises(FileNotFoundError):
        manager.list_files_in_directory("/nonexistent/directory", 'pdf')


def test_document_manager_invalid_file_type():
    """Test error handling for invalid file type."""
    from agent.tools.documents import DocumentManager
    import tempfile
    
    manager = DocumentManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError, match="Unsupported file type"):
            manager.list_files_in_directory(tmp_dir, 'invalid')


def test_merge_command_requires_directory():
    """Test that merge command prompts for directory."""
    result = runner.invoke(app, ["merge", "pdf"], input="\n")
    assert "Enter directory path" in result.stdout or result.exit_code != 0


def test_convert_command_requires_input():
    """Test that convert command prompts for input file."""
    result = runner.invoke(app, ["convert", "pdf-to-docx"], input="\n")
    assert "Enter input file path" in result.stdout or result.exit_code != 0
