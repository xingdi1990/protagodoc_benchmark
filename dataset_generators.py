"""
Dataset Generators for OLMoCR-Bench Style Test Cases

This module contains generators for different types of test cases:
- Text presence/absence tests
- Reading order tests  
- Table relationship tests
- Mathematical equation tests
- Header/footer detection tests
"""

import base64
import json
import random
import re
import uuid
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import numpy as np
from bs4 import BeautifulSoup
from openai import OpenAI
from PIL import Image
from pypdf import PdfReader


class PDFProcessor:
    """Utility class for PDF processing operations."""
    
    def pdf_to_image(self, pdf_path: str, page_num: int, target_dim: int = 2048) -> Optional[str]:
        """Convert PDF page to base64 encoded image.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            target_dim: Target dimension for longest side
            
        Returns:
            Base64 encoded PNG image string, or None if failed
        """
        try:
            import fitz  # PyMuPDF
            
            # Open PDF
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]  # Convert to 0-indexed
            
            # Calculate zoom to achieve target dimension
            rect = page.rect
            zoom = target_dim / max(rect.width, rect.height)
            mat = fitz.Matrix(zoom, zoom)
            
            # Render page to image
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            doc.close()
            return img_base64
            
        except ImportError:
            print("PyMuPDF not installed. Install with: pip install PyMuPDF")
            return None
        except Exception as e:
            print(f"Error converting PDF to image: {str(e)}")
            return None
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF."""
        try:
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {str(e)}")
            return 0
    
    def extract_text(self, pdf_path: str, page_num: int) -> str:
        """Extract text from a PDF page."""
        try:
            reader = PdfReader(pdf_path)
            page = reader.pages[page_num - 1]  # Convert to 0-indexed
            return page.extract_text()
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""


class BaseTestGenerator(ABC):
    """Base class for test generators."""
    
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
    
    @abstractmethod
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate test cases for a PDF page."""
        pass
    
    def _make_gpt_request(self, messages: List[Dict], response_format: Optional[Dict] = None) -> Optional[str]:
        """Make a request to GPT with error handling."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4000
            }
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error making GPT request: {str(e)}")
            return None


class TextPresenceGenerator(BaseTestGenerator):
    """Generates text presence and absence tests."""
    
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate text presence/absence tests."""
        tests = []
        pdf_name = pdf_path.split('/')[-1]
        
        # First, extract sentences from the document
        sentences = self._extract_sentences(image_base64)
        if not sentences:
            return tests
        
        # Generate presence tests: treat max_tests as per-label budget
        presence_budget = max_tests
        presence_candidates = list(sentences)
        random.shuffle(presence_candidates)

        present_added = 0
        for sentence in presence_candidates:
            if present_added >= presence_budget:
                break
            clean_sentence = self._clean_sentence(sentence)
            if len(clean_sentence) < 10:
                continue

            test_id = f"{pdf_name.replace('.pdf', '')}_present_{uuid.uuid4().hex[:8]}"
            max_diffs = max(1, len(clean_sentence) // 20)

            tests.append({
                "pdf": pdf_name,
                "page": page_num,
                "id": test_id,
                "type": "present",
                "text": clean_sentence,
                "max_diffs": max_diffs,
                "checked": "unverified"
            })
            present_added += 1

        # Generate absence tests (headers/footers/page numbers): independent per-label budget
        absence_tests = self._generate_absence_tests(pdf_path, page_num, image_base64, max_tests)
        tests.extend(absence_tests)
        
        return tests
    
    def _extract_sentences(self, image_base64: str) -> List[str]:
        """Extract sentences from the document image."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this document page and extract 5-10 complete, meaningful sentences that appear in the main content. 
                        
                        Focus on:
                        - Complete sentences (not fragments)
                        - Main body text (not headers, footers, captions)
                        - Sentences that are at least 10 words long
                        - Diverse content from different parts of the page
                        
                        Return as a JSON array of strings. Example:
                        ["First complete sentence here.", "Second complete sentence here."]"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "sentence_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "sentences": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["sentences"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                return data.get("sentences", [])
            except json.JSONDecodeError:
                pass
        
        return []
    
    def _generate_absence_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate tests for text that should be absent (headers/footers)."""
        tests = []
        pdf_name = pdf_path.split('/')[-1]
        
        # Extract potential headers/footers
        headers_footers = self._extract_headers_footers(image_base64)
        
        for i, text in enumerate(headers_footers[:max_tests]):
            test_id = f"{pdf_name.replace('.pdf', '')}_absent_{uuid.uuid4().hex[:8]}"
            
            tests.append({
                "pdf": pdf_name,
                "page": page_num,
                "id": test_id,
                "type": "absent",
                "text": text,
                "checked": "unverified"
            })
        
        return tests
    
    def _extract_headers_footers(self, image_base64: str) -> List[str]:
        """Extract potential headers and footers."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Identify headers, footers, page numbers, and other metadata text that should typically be excluded from OCR output.
                        
                        Look for:
                        - Page numbers
                        - Journal/publication names
                        - Website URLs
                        - Copyright notices
                        - Headers with author names or titles
                        - Footer text like "Downloaded from..." or dates
                        
                        Return as a JSON array of strings. Example:
                        ["Page 1", "www.example.com", "© 2024 Publisher"]"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "header_footer_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "headers_footers": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["headers_footers"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                return data.get("headers_footers", [])
            except json.JSONDecodeError:
                pass
        
        return []
    
    def _clean_sentence(self, sentence: str) -> str:
        """Clean and normalize a sentence."""
        # Remove extra whitespace
        sentence = re.sub(r'\s+', ' ', sentence.strip())
        # Remove very long sentences (likely errors)
        if len(sentence) > 200:
            sentence = sentence[:200] + "..."
        return sentence


class TextOrderGenerator(BaseTestGenerator):
    """Generates reading order tests."""
    
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate reading order tests."""
        tests = []
        pdf_name = pdf_path.split('/')[-1]
        
        # Extract sentence pairs in reading order
        sentence_pairs = self._extract_ordered_pairs(image_base64, max_tests)
        
        # Validate that pairs are in the same region using the paper's exact criteria
        validated_pairs = self._validate_same_region_pairs(sentence_pairs, image_base64)
        
        for i, (before, after) in enumerate(validated_pairs):
            test_id = f"{pdf_name.replace('.pdf', '')}_order_{uuid.uuid4().hex[:8]}"
            max_diffs = max(2, max(len(before), len(after)) // 20)
            
            tests.append({
                "pdf": pdf_name,
                "page": page_num,
                "id": test_id,
                "type": "order",
                "before": before,
                "after": after,
                "max_diffs": max_diffs,
                "checked": "unverified"
            })
        
        return tests
    
    def _extract_ordered_pairs(self, image_base64: str, max_pairs: int) -> List[Tuple[str, str]]:
        """Extract pairs of sentences that should appear in order."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze this document and identify {max_pairs} pairs of text segments that should appear in natural reading order WITHIN THE SAME REGION OR COLUMN.
                        
                        CRITICAL: Both texts in each pair must be located in the same region of the page (same column, same section, same continuous text flow). Do NOT create pairs from different regions, different columns, or separate text boxes.
                        
                        Each pair should:
                        - Be from the main content (not headers/footers)  
                        - Be in the SAME region/column/section of the page
                        - Represent natural reading flow within that region
                        - Be meaningful text segments (at least 8 words each)
                        - Have clear sequential order within the same text flow
                        
                        Look at the page layout and identify regions like:
                        - Text columns that flow continuously
                        - Sections within the same article/document body
                        - Paragraphs in the same logical section
                        
                        Return as JSON with pairs in reading order. Example:
                        {{"pairs": [
                            {{"before": "First sentence in left column.", "after": "Next sentence in same left column."}},
                            {{"before": "Earlier paragraph in main text.", "after": "Following paragraph in same section."}}
                        ]}}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "order_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "pairs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "before": {"type": "string"},
                                    "after": {"type": "string"}
                                },
                                "required": ["before", "after"]
                            }
                        }
                    },
                    "required": ["pairs"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                pairs = data.get("pairs", [])
                return [(p["before"], p["after"]) for p in pairs]
            except (json.JSONDecodeError, KeyError):
                pass
        
        return []
    
    def _validate_same_region_pairs(self, sentence_pairs: List[Tuple[str, str]], image_base64: str) -> List[Tuple[str, str]]:
        """Validate that sentence pairs are in the same region using the paper's exact criteria."""
        if not sentence_pairs:
            return []
        
        validated_pairs = []
        
        print(f"Validating {len(sentence_pairs)} order test pairs for same-region criteria...")
        
        for i, (before_text, after_text) in enumerate(sentence_pairs):
            if self._validate_same_region(before_text, after_text, image_base64):
                validated_pairs.append((before_text, after_text))
                print(f"✓ Pair {i+1}: VALID (same region)")
            else:
                print(f"✗ Pair {i+1}: FILTERED (different regions)")
        
        print(f"Validation complete: {len(validated_pairs)}/{len(sentence_pairs)} pairs kept")
        return validated_pairs
    
    def _validate_same_region(self, before_text: str, after_text: str, image_base64: str) -> bool:
        """Validate that two texts are in the same region using the paper's exact prompt."""
        # Truncate texts if too long for the API
        before_display = before_text[:100] + "..." if len(before_text) > 100 else before_text
        after_display = after_text[:100] + "..." if len(after_text) > 100 else after_text
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Does the text in the 'before' field and the 'after' field appear in the same region of the page?

Look at the PDF image and determine if these texts are located near each other or in completely different parts of the page. Different regions could be the captions for different images, or inside of different insets or tables. However, appearing the same column of text, or in the naturally flowing next column of text is close enough.

Before: {before_display}
After: {after_display}

Respond with 'YES' if they appear in the same region or column, and 'NO' if they appear in different regions. Then explain your reasoning in 1-2 sentences."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response = self._make_gpt_request(messages)
        if response:
            # Check if response starts with "YES"
            return response.strip().upper().startswith("YES")
        
        # If API fails, assume it's valid (conservative approach)
        return True


class TableTestGenerator(BaseTestGenerator):
    """Generates table relationship tests."""
    
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate table relationship tests."""
        tests = []
        pdf_name = pdf_path.split('/')[-1]
        
        # First detect if there are tables
        table_data = self._detect_tables(image_base64)
        if not table_data:
            return tests
        
        # Generate relationship tests
        relationships = self._generate_table_relationships(image_base64, table_data, max_tests)
        
        for i, rel in enumerate(relationships):
            # Create ID in format: filename_table_##
            test_id = f"{pdf_name.replace('.pdf', '')}_table_{i:02d}"
            
            test = {
                "pdf": pdf_name,
                "page": page_num,
                "id": test_id,
                "type": "table",
                "max_diffs": 0,
                "checked": "unverified",
                "cell": rel["cell"]
            }
            
            # Add all relationship properties, setting to null if not present
            for key in ["up", "down", "left", "right", "top_heading", "left_heading"]:
                test[key] = rel.get(key, None)
            
            # Add URL field (set to null since we don't have source URLs)
            test["url"] = None
            
            tests.append(test)
        
        return tests
    
    def _detect_tables(self, image_base64: str) -> Optional[Dict]:
        """Detect tables in the document."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this document for tables. If tables are present, identify their structure and content.
                        
                        Return information about tables found, including:
                        - Whether tables exist
                        - Basic structure information
                        - Sample cell values
                        
                        Return as JSON. Example:
                        {"has_tables": true, "table_count": 1, "description": "Table with financial data"}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "table_detection",
                "schema": {
                    "type": "object",
                    "properties": {
                        "has_tables": {"type": "boolean"},
                        "table_count": {"type": "integer"},
                        "description": {"type": "string"}
                    },
                    "required": ["has_tables"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                return data if data.get("has_tables") else None
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _generate_table_relationships(self, image_base64: str, table_data: Dict, max_tests: int) -> List[Dict]:
        """Generate table cell relationship tests."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Generate {max_tests} table relationship tests from the tables in this document.
                        
                        For each test, identify a cell and its relationship to other cells. IMPORTANT: You must provide ALL relationship fields for each cell, using null for missing relationships:
                        - up/down: cells directly above/below (null if no cell exists)
                        - left/right: cells directly to the left/right (null if no cell exists)  
                        - top_heading: column header for this cell (null if no header)
                        - left_heading: row header for this cell (null if no header)
                        
                        Return as JSON with explicit null values. Example:
                        {{
                            "relationships": [
                                {{"cell": "3.32T", "up": null, "down": "2.1T", "left": "3.71T", "right": null, "top_heading": "Words", "left_heading": null}},
                                {{"cell": "arXiv", "up": "Sources", "down": null, "left": null, "right": "47.2B", "top_heading": "Source", "left_heading": "Dataset"}}
                            ]
                        }}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "table_relationships",
                "schema": {
                    "type": "object",
                    "properties": {
                        "relationships": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "cell": {"type": "string"},
                                    "up": {"type": ["string", "null"]},
                                    "down": {"type": ["string", "null"]},
                                    "left": {"type": ["string", "null"]},
                                    "right": {"type": ["string", "null"]},
                                    "top_heading": {"type": ["string", "null"]},
                                    "left_heading": {"type": ["string", "null"]}
                                },
                                "required": ["cell", "up", "down", "left", "right", "top_heading", "left_heading"]
                            }
                        }
                    },
                    "required": ["relationships"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                return data.get("relationships", [])
            except json.JSONDecodeError:
                pass
        
        return []


class MathTestGenerator(BaseTestGenerator):
    """Generates mathematical equation tests."""
    
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate math equation tests."""
        tests = []
        pdf_name = pdf_path.split('/')[-1]
        
        # Extract mathematical equations
        equations = self._extract_equations(image_base64, max_tests)
        
        for i, equation in enumerate(equations):
            test_id = f"{pdf_name.replace('.pdf', '')}_math_{uuid.uuid4().hex[:8]}"
            
            tests.append({
                "pdf": pdf_name,
                "page": page_num,
                "id": test_id,
                "type": "math",
                "math": equation,
                "checked": "unverified"
            })
        
        return tests
    
    def _extract_equations(self, image_base64: str, max_equations: int) -> List[str]:
        """Extract mathematical equations from the document."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Identify and extract up to {max_equations} mathematical equations from this document.
                        
                        IMPORTANT: Only extract actual mathematical equations, NOT table content or table markup.
                        
                        Convert each equation to proper LaTeX format that would work with KaTeX:
                        - Use proper LaTeX syntax (no table pipes | or HTML)
                        - Focus on mathematical expressions with operators (+, -, ×, ÷, =, etc.)
                        - Use \\times for multiplication, \\div for division
                        - Use proper LaTeX formatting for fractions, exponents, etc.
                        - Avoid extracting table cells or non-mathematical content
                        
                        Examples of GOOD equations:
                        - "2 + 3 = 5"
                        - "x^2 + y^2 = z^2" 
                        - "\\frac{{a}}{{b}} = c"
                        - "1.5^{{\\circ}}C"
                        
                        Examples of BAD (avoid these):
                        - "| 1,544,382 | \\"
                        - Table content with pipes
                        - Non-mathematical text
                        
                        Return as JSON array of LaTeX strings. If no valid mathematical equations found, return empty array."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ]
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "math_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "equations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["equations"]
                }
            }
        }
        
        response = self._make_gpt_request(messages, response_format)
        if response:
            try:
                data = json.loads(response)
                equations = data.get("equations", [])
                # Filter out invalid equations
                valid_equations = []
                for eq in equations:
                    if self._is_valid_math_equation(eq):
                        valid_equations.append(eq)
                return valid_equations
            except json.JSONDecodeError:
                pass
        
        return []
    
    def _is_valid_math_equation(self, equation: str) -> bool:
        """Validate that an equation is proper LaTeX math, not table content."""
        # Remove whitespace
        eq = equation.strip()
        
        # Skip empty equations
        if not eq:
            return False
        
        # Skip if it contains table markup
        if '|' in eq or '<br>' in eq or 'Total<br>' in eq:
            return False
        
        # Skip if it's too long (likely table content)
        if len(eq) > 100:
            return False
        
        # Must contain mathematical operators or symbols
        math_indicators = ['+', '-', '=', '\\times', '\\div', '^', '_', '\\frac', '\\int', '\\sum']
        if not any(indicator in eq for indicator in math_indicators):
            return False
        
        # Should not contain common table words
        table_words = ['Total', 'Expenses', 'Assets', 'Net', 'Class', 'Unit']
        if any(word in eq for word in table_words):
            return False
        
        return True


class HeaderFooterGenerator(BaseTestGenerator):
    """Generates header/footer detection tests."""
    
    def generate_tests(self, pdf_path: str, page_num: int, image_base64: str, max_tests: int) -> List[Dict]:
        """Generate header/footer tests (absence tests)."""
        # This is handled by TextPresenceGenerator's absence tests
        return []
