"""
Document utilities for CloneAI
Supports merging PDFs and PPTs, and converting between formats.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
from copy import deepcopy
from copy import deepcopy
# NOTE: Heavy / optional dependencies are imported lazily inside functions so
# that email/calendar functionality still works even if doc utilities deps
# are not installed in the current environment.

# Types imported conditionally
try:  # Light dependency; usually present once installed
    from PyPDF2 import PdfMerger  # type: ignore
except Exception:  # pragma: no cover
    PdfMerger = None  # type: ignore

# Placeholders for optional modules
Presentation = None  # set when imported
Converter = None     # set when imported
comtypes = None      # set when imported


class DocumentManager:
    """Manager for document operations (merge, convert)."""
    
    def __init__(self):
        """Initialize document manager."""
        self.supported_pdf_formats = ['.pdf']
        self.supported_ppt_formats = ['.pptx', '.ppt']
        self.supported_doc_formats = ['.docx', '.doc']
    
    def list_files_in_directory(self, directory: str, file_type: str) -> List[Tuple[str, datetime]]:
        """
        List all files of a specific type in a directory with their modification times.
        
        Args:
            directory: Path to directory
            file_type: 'pdf', 'ppt', or 'docx'
            
        Returns:
            List of tuples (filename, modification_time)
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if file_type == 'pdf':
            extensions = self.supported_pdf_formats
        elif file_type == 'ppt':
            extensions = self.supported_ppt_formats
        elif file_type == 'docx':
            extensions = self.supported_doc_formats
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        files = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file)
                if ext.lower() in extensions:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    files.append((file, mod_time))
        
        return files
    
    def merge_pdfs(
        self,
        directory: str,
        output_path: str,
        file_list: Optional[List[str]] = None,
        start_file: Optional[str] = None,
        end_file: Optional[str] = None,
        order: str = 'asc'
    ) -> str:
        """
        Merge multiple PDF files into one.
        
        Args:
            directory: Directory containing PDF files
            output_path: Path for the output merged PDF
            file_list: Specific list of PDF filenames to merge (in order)
            start_file: Start file for range merge
            end_file: End file for range merge
            order: 'asc' for chronological, 'desc' for reverse chronological
            
        Returns:
            Path to merged PDF
        """
        if PdfMerger is None:
            raise ImportError(
                "PyPDF2 is not installed in the active environment. Activate your venv and run: pip install PyPDF2"
            )

        merger = PdfMerger()
        
        try:
            # Get files to merge
            if file_list:
                # Use specific file list
                files_to_merge = [(f, None) for f in file_list]
            elif start_file and end_file:
                # Get range of files
                all_files = self.list_files_in_directory(directory, 'pdf')
                all_files.sort(key=lambda x: x[1])  # Sort by modification time
                
                # Find indices
                start_idx = None
                end_idx = None
                for idx, (filename, _) in enumerate(all_files):
                    if filename == start_file:
                        start_idx = idx
                    if filename == end_file:
                        end_idx = idx
                
                if start_idx is None:
                    raise ValueError(f"Start file not found: {start_file}")
                if end_idx is None:
                    raise ValueError(f"End file not found: {end_file}")
                
                # Ensure start comes before end
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                
                files_to_merge = all_files[start_idx:end_idx + 1]
            else:
                # Get all PDFs in directory
                files_to_merge = self.list_files_in_directory(directory, 'pdf')
                files_to_merge.sort(key=lambda x: x[1])  # Sort by modification time
            
            # Apply order
            if order == 'desc':
                files_to_merge.reverse()
            
            # Merge PDFs
            if not files_to_merge:
                raise ValueError("No PDF files found to merge")
            
            for filename, _ in files_to_merge:
                file_path = os.path.join(directory, filename)
                merger.append(file_path)
            
            # Write output (guard empty dirname for current directory)
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            merger.write(output_path)
            merger.close()
            
            return output_path
        
        except Exception as e:
            merger.close()
            raise Exception(f"Error merging PDFs: {str(e)}")
    
    def merge_ppts(
        self,
        directory: str,
        output_path: str,
        file_list: Optional[List[str]] = None,
        start_file: Optional[str] = None,
        end_file: Optional[str] = None,
        order: str = 'asc'
    ) -> str:
        """
        Merge multiple PowerPoint files into one.
        
        Args:
            directory: Directory containing PPTX files
            output_path: Path for the output merged PPTX
            file_list: Specific list of PPTX filenames to merge (in order)
            start_file: Start file for range merge
            end_file: End file for range merge
            order: 'asc' for chronological, 'desc' for reverse chronological
            
        Returns:
            Path to merged PPTX
        """
        try:
            global Presentation
            if Presentation is None:
                try:
                    from pptx import Presentation as _Presentation  # type: ignore
                    Presentation = _Presentation
                except Exception as ie:
                    raise ImportError(
                        "python-pptx is not installed in the active environment. Activate your venv and run: pip install python-pptx"
                    ) from ie
            # Get files to merge
            if file_list:
                files_to_merge = [(f, None) for f in file_list]
            elif start_file and end_file:
                all_files = self.list_files_in_directory(directory, 'ppt')
                all_files.sort(key=lambda x: x[1])
                
                start_idx = None
                end_idx = None
                for idx, (filename, _) in enumerate(all_files):
                    if filename == start_file:
                        start_idx = idx
                    if filename == end_file:
                        end_idx = idx
                
                if start_idx is None:
                    raise ValueError(f"Start file not found: {start_file}")
                if end_idx is None:
                    raise ValueError(f"End file not found: {end_file}")
                
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                
                files_to_merge = all_files[start_idx:end_idx + 1]
            else:
                files_to_merge = self.list_files_in_directory(directory, 'ppt')
                files_to_merge.sort(key=lambda x: x[1])
            
            if order == 'desc':
                files_to_merge.reverse()
            
            if not files_to_merge:
                raise ValueError("No PowerPoint files found to merge")
            
            # Merge presentations by copying slide XML elements
            # Start with an empty presentation
            merged_prs = Presentation()
            
            # Process each source presentation
            for filename, _ in files_to_merge:
                file_path = os.path.join(directory, filename)
                source_prs = Presentation(file_path)
                
                # Copy each slide from source to merged presentation
                for slide in source_prs.slides:
                    # Get the slide layout (use blank layout from merged prs)
                    # Layout index 6 is typically blank, fallback to 0
                    try:
                        blank_layout = merged_prs.slide_layouts[6]
                    except IndexError:
                        blank_layout = merged_prs.slide_layouts[0]
                    
                    # Add new slide
                    new_slide = merged_prs.slides.add_slide(blank_layout)
                    
                    # Copy all shapes from source slide to new slide
                    for shape in slide.shapes:
                        # Clone the shape element
                        el = shape.element
                        newel = deepcopy(el)
                        new_slide.shapes._spTree.insert_element_before(newel, 'p:extLst')
            
            # If no slides were added (all source files were empty), add one blank slide
            if len(merged_prs.slides) == 0:
                try:
                    blank_layout = merged_prs.slide_layouts[6]
                except IndexError:
                    blank_layout = merged_prs.slide_layouts[0]
                merged_prs.slides.add_slide(blank_layout)
            
            # Save merged presentation
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            merged_prs.save(output_path)
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Error merging PowerPoints: {str(e)}")
    
    def convert_pdf_to_docx(self, pdf_path: str, output_path: str) -> str:
        """
        Convert PDF to DOCX.
        
        Args:
            pdf_path: Path to input PDF
            output_path: Path for output DOCX
            
        Returns:
            Path to converted DOCX
        """
        try:
            global Converter
            if Converter is None:
                try:
                    from pdf2docx import Converter as _Converter  # type: ignore
                    Converter = _Converter
                except Exception as ie:
                    raise ImportError(
                        "pdf2docx is not installed in the active environment. Activate your venv and run: pip install pdf2docx"
                    ) from ie
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            
            # Convert PDF to DOCX
            cv = Converter(pdf_path)
            cv.convert(output_path)
            cv.close()
            
            return output_path
        
        except Exception as e:
            raise Exception(f"Error converting PDF to DOCX: {str(e)}")
    
    def convert_docx_to_pdf(self, docx_path: str, output_path: str) -> str:
        """
        Convert DOCX to PDF using Microsoft Word COM automation (Windows only).
        
        Args:
            docx_path: Path to input DOCX
            output_path: Path for output PDF
            
        Returns:
            Path to converted PDF
        """
        try:
            global comtypes
            if comtypes is None:
                try:
                    import comtypes.client as comtypes  # type: ignore
                except Exception as ie:
                    raise ImportError(
                        "comtypes is not installed. Activate your venv and run: pip install comtypes (Windows only)."
                    ) from ie
            if not os.path.exists(docx_path):
                raise FileNotFoundError(f"DOCX file not found: {docx_path}")
            
            import sys
            if sys.platform != 'win32':
                raise NotImplementedError("DOCX to PDF conversion is only supported on Windows")
            
            # Use absolute paths
            docx_path = os.path.abspath(docx_path)
            output_path = os.path.abspath(output_path)
            
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            
            # Initialize Word application
            word = comtypes.client.CreateObject('Word.Application')
            word.Visible = False
            
            try:
                # Open document
                doc = word.Documents.Open(docx_path)
                
                # Save as PDF (format 17 is PDF)
                doc.SaveAs(output_path, FileFormat=17)
                doc.Close()
                
                return output_path
            finally:
                word.Quit()
        
        except Exception as e:
            raise Exception(f"Error converting DOCX to PDF: {str(e)}")
    
    def convert_ppt_to_pdf(self, ppt_path: str, output_path: str) -> str:
        """
        Convert PPT/PPTX to PDF using Microsoft PowerPoint COM automation (Windows only).
        
        Args:
            ppt_path: Path to input PPT/PPTX
            output_path: Path for output PDF
            
        Returns:
            Path to converted PDF
        """
        try:
            global comtypes, Presentation
            if comtypes is None:
                try:
                    import comtypes.client as comtypes  # type: ignore
                except Exception as ie:
                    raise ImportError(
                        "comtypes is not installed. Activate venv and run: pip install comtypes (Windows only)."
                    ) from ie
            if Presentation is None:
                try:
                    from pptx import Presentation as _Presentation  # type: ignore
                    Presentation = _Presentation
                except Exception as ie:
                    raise ImportError(
                        "python-pptx is not installed. Activate venv and run: pip install python-pptx"
                    ) from ie
            if not os.path.exists(ppt_path):
                raise FileNotFoundError(f"PowerPoint file not found: {ppt_path}")
            
            import sys
            if sys.platform != 'win32':
                raise NotImplementedError("PPT to PDF conversion is only supported on Windows")
            
            # Use absolute paths
            ppt_path = os.path.abspath(ppt_path)
            output_path = os.path.abspath(output_path)
            
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            
            # Initialize PowerPoint application
            powerpoint = comtypes.client.CreateObject('PowerPoint.Application')
            powerpoint.Visible = 1
            
            try:
                # Open presentation
                presentation = powerpoint.Presentations.Open(ppt_path, WithWindow=False)
                
                # Save as PDF (format 32 is PDF)
                presentation.SaveAs(output_path, 32)
                presentation.Close()
                
                return output_path
            finally:
                powerpoint.Quit()
        
        except Exception as e:
            raise Exception(f"Error converting PPT to PDF: {str(e)}")


# Public wrapper functions
def merge_pdf_files(
    directory: str,
    output_path: str,
    file_list: Optional[List[str]] = None,
    start_file: Optional[str] = None,
    end_file: Optional[str] = None,
    order: str = 'asc'
) -> str:
    """Merge PDF files."""
    manager = DocumentManager()
    return manager.merge_pdfs(directory, output_path, file_list, start_file, end_file, order)


def merge_ppt_files(
    directory: str,
    output_path: str,
    file_list: Optional[List[str]] = None,
    start_file: Optional[str] = None,
    end_file: Optional[str] = None,
    order: str = 'asc'
) -> str:
    """Merge PowerPoint files."""
    manager = DocumentManager()
    return manager.merge_ppts(directory, output_path, file_list, start_file, end_file, order)


def convert_pdf_to_docx(pdf_path: str, output_path: str) -> str:
    """Convert PDF to DOCX."""
    manager = DocumentManager()
    return manager.convert_pdf_to_docx(pdf_path, output_path)


def convert_docx_to_pdf(docx_path: str, output_path: str) -> str:
    """Convert DOCX to PDF."""
    manager = DocumentManager()
    return manager.convert_docx_to_pdf(docx_path, output_path)


def convert_ppt_to_pdf(ppt_path: str, output_path: str) -> str:
    """Convert PPT/PPTX to PDF."""
    manager = DocumentManager()
    return manager.convert_ppt_to_pdf(ppt_path, output_path)


def list_documents_in_directory(directory: str, file_type: str) -> List[Tuple[str, datetime]]:
    """List documents in directory with timestamps."""
    manager = DocumentManager()
    return manager.list_files_in_directory(directory, file_type)
