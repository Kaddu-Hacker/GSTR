"""Auto-mapping engine with header similarity matching"""

import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
from canonical_fields import CANONICAL_FIELDS
from models_canonical import HeaderMapping


class HeaderMatcher:
    """Matches file headers to canonical fields using multiple strategies"""
    
    def __init__(self, canonical_fields: Dict[str, List[str]] = None):
        self.canonical_fields = canonical_fields or CANONICAL_FIELDS
        
    def normalize_header(self, header: str) -> str:
        """Normalize header: lowercase, remove punctuation, trim"""
        if not header:
            return ""
        # Convert to lowercase
        normalized = header.lower().strip()
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        # Remove common punctuation but keep meaningful chars
        normalized = re.sub(r'[\(\)\[\]{}"\'°]', '', normalized)
        return normalized
    
    def exact_match(self, header: str, canonical_field: str) -> float:
        """Check for exact match"""
        header_norm = self.normalize_header(header)
        for synonym in self.canonical_fields.get(canonical_field, []):
            synonym_norm = self.normalize_header(synonym)
            if header_norm == synonym_norm:
                return 1.0
        return 0.0
    
    def substring_match(self, header: str, canonical_field: str) -> float:
        """Check if header or synonym is substring of the other"""
        header_norm = self.normalize_header(header)
        for synonym in self.canonical_fields.get(canonical_field, []):
            synonym_norm = self.normalize_header(synonym)
            if header_norm in synonym_norm or synonym_norm in header_norm:
                # Higher score if longer match
                shorter = min(len(header_norm), len(synonym_norm))
                longer = max(len(header_norm), len(synonym_norm))
                return 0.85 + (0.1 * shorter / longer)
        return 0.0
    
    def fuzzy_match(self, header: str, canonical_field: str) -> float:
        """Use fuzzy string matching (Levenshtein-like)"""
        header_norm = self.normalize_header(header)
        best_score = 0.0
        
        for synonym in self.canonical_fields.get(canonical_field, []):
            synonym_norm = self.normalize_header(synonym)
            # Use SequenceMatcher for similarity
            ratio = SequenceMatcher(None, header_norm, synonym_norm).ratio()
            if ratio > best_score:
                best_score = ratio
        
        # Scale fuzzy scores to 0.7-0.85 range to differentiate from exact matches
        if best_score >= 0.75:
            return 0.70 + (best_score - 0.75) * 0.6  # Maps 0.75-1.0 to 0.70-0.85
        return 0.0
    
    def match_header(self, header: str) -> Optional[Tuple[str, float, str]]:
        """
        Match a single header to best canonical field
        
        Returns:
            (canonical_field, confidence_score, match_type) or None
        """
        best_match = None
        best_score = 0.0
        best_type = None
        
        for canonical_field in self.canonical_fields.keys():
            # Try exact match first
            score = self.exact_match(header, canonical_field)
            if score > best_score:
                best_score = score
                best_match = canonical_field
                best_type = "exact"
            
            # Try substring match
            if score == 0.0:  # Only if exact didn't match
                score = self.substring_match(header, canonical_field)
                if score > best_score:
                    best_score = score
                    best_match = canonical_field
                    best_type = "substring"
            
            # Try fuzzy match
            if score == 0.0:  # Only if others didn't match
                score = self.fuzzy_match(header, canonical_field)
                if score > best_score:
                    best_score = score
                    best_match = canonical_field
                    best_type = "fuzzy"
        
        # Only return matches with confidence >= 0.7
        if best_match and best_score >= 0.70:
            return (best_match, best_score, best_type)
        
        return None
    
    def map_headers(self, headers: List[str]) -> Dict[str, HeaderMapping]:
        """
        Map all headers to canonical fields
        
        Returns:
            Dict mapping file_header -> HeaderMapping
        """
        mappings = {}
        
        for header in headers:
            match = self.match_header(header)
            if match:
                canonical_field, confidence, match_type = match
                mappings[header] = HeaderMapping(
                    file_header=header,
                    canonical_field=canonical_field,
                    confidence=confidence,
                    match_type=match_type
                )
        
        return mappings
    
    def calculate_coverage(self, mappings: Dict[str, HeaderMapping], required_fields: List[str]) -> float:
        """
        Calculate how well the mappings cover required fields
        
        Returns:
            Coverage score 0-1 (1 = all required fields mapped)
        """
        if not required_fields:
            return 1.0
        
        mapped_canonical = {m.canonical_field for m in mappings.values()}
        covered = sum(1 for field in required_fields if field in mapped_canonical)
        
        return covered / len(required_fields)
    
    def suggest_section(self, headers: List[str]) -> Optional[str]:
        """
        Suggest which GSTR-1 section this file belongs to based on headers
        
        Returns:
            Section name (e.g., 'b2b', 'b2cs', 'hsn') or None
        """
        from canonical_fields import SECTION_RULES
        
        mappings = self.map_headers(headers)
        mapped_fields = {m.canonical_field for m in mappings.values()}
        
        best_section = None
        best_coverage = 0.0
        
        for section, rules in SECTION_RULES.items():
            required = rules.get("required_fields", [])
            if required:
                coverage = self.calculate_coverage(mappings, required)
                if coverage > best_coverage and coverage >= 0.75:
                    best_coverage = coverage
                    best_section = section
        
        return best_section


def create_meesho_mapping_template():
    """Create pre-configured mapping template for Meesho files"""
    from models_canonical import MappingTemplate, HeaderMapping, FileType
    
    meesho_tcs_sales = MappingTemplate(
        name="Meesho TCS Sales",
        platform="meesho",
        file_type=FileType.TCS_SALES,
        mappings=[
            HeaderMapping(file_header="gst_rate", canonical_field="gst_rate", confidence=1.0, match_type="exact"),
            HeaderMapping(file_header="total_taxable_sale_value", canonical_field="taxable_value", confidence=1.0, match_type="exact"),
            HeaderMapping(file_header="end_customer_state_new", canonical_field="place_of_supply", confidence=1.0, match_type="exact"),
        ]
    )
    
    return meesho_tcs_sales
