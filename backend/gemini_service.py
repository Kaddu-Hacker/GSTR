"""
Gemini AI Service for GST Filing Enhancement
Uses Gemini to detect missing invoices and provide insights
"""
import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path
import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Use free model: gemini-2.0-flash-exp (or gemini-1.5-flash)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

logger = logging.getLogger(__name__)


class GeminiService:
    """AI-powered service for GST filing enhancements"""
    
    @staticmethod
    def detect_missing_invoices(invoice_numbers: List[str]) -> Dict:
        """
        Use Gemini AI to intelligently detect missing invoice numbers
        Returns comprehensive analysis with missing numbers and patterns
        """
        try:
            if not invoice_numbers or len(invoice_numbers) == 0:
                return {
                    "missing_invoices": [],
                    "analysis": "No invoice numbers provided",
                    "confidence": "low"
                }
            
            # Prepare prompt for Gemini
            prompt = f"""
You are an AI assistant helping with GST filing for an e-commerce seller in India. 
Analyze the following list of invoice numbers and detect any missing sequences or gaps.

Invoice Numbers: {json.dumps(invoice_numbers[:100])}  

Task:
1. Identify invoice number patterns (prefixes, serial numbers)
2. Detect missing invoice numbers in sequences
3. Find any anomalies or irregularities
4. Provide insights on invoice numbering quality

Return your analysis in JSON format with these fields:
{{
    "patterns_detected": ["pattern1", "pattern2"],
    "missing_invoices": ["INV001", "INV005"],
    "missing_count": 2,
    "total_analyzed": 50,
    "anomalies": ["description of any issues"],
    "recommendations": ["suggestion1", "suggestion2"],
    "confidence": "high/medium/low"
}}

Be concise and accurate. Only include actual missing numbers in sequences.
"""
            
            # Call Gemini
            response = model.generate_content(prompt)
            
            # Parse response
            try:
                # Extract JSON from response
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                analysis = json.loads(response_text)
                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, return structured fallback
                return {
                    "missing_invoices": [],
                    "analysis": response.text[:500],
                    "confidence": "medium",
                    "note": "AI provided text analysis instead of structured data"
                }
        
        except Exception as e:
            logger.error(f"Gemini analysis error: {str(e)}")
            return {
                "missing_invoices": [],
                "error": str(e),
                "confidence": "low"
            }
    
    @staticmethod
    def validate_gst_calculations(summary_data: Dict) -> Dict:
        """
        Use Gemini to validate GST calculations and provide insights
        """
        try:
            prompt = f"""
You are a GST compliance expert in India. Review this GST filing summary and validate:

Summary Data:
{json.dumps(summary_data, indent=2)}

Task:
1. Verify if CGST + SGST values are correct (should be equal for intra-state)
2. Check if IGST is correctly applied for inter-state transactions
3. Validate if taxable value × GST rate = tax amount
4. Identify any calculation errors or inconsistencies
5. Provide recommendations for compliance

Return JSON:
{{
    "validation_status": "pass/warning/fail",
    "issues_found": ["issue1", "issue2"],
    "recommendations": ["rec1", "rec2"],
    "compliance_score": 95,
    "summary": "Brief overview"
}}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean markdown
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            try:
                validation = json.loads(response_text)
                return validation
            except:
                return {
                    "validation_status": "pass",
                    "summary": response.text[:300],
                    "note": "AI provided text analysis"
                }
        
        except Exception as e:
            logger.error(f"Gemini validation error: {str(e)}")
            return {
                "validation_status": "unknown",
                "error": str(e)
            }
    
    @staticmethod
    def generate_filing_insights(invoice_data: List[Dict]) -> Dict:
        """
        Generate AI-powered insights and recommendations for GST filing
        """
        try:
            # Prepare summary for AI
            total_invoices = len(invoice_data)
            total_taxable = sum(inv.get('taxable_value', 0) for inv in invoice_data)
            total_tax = sum(inv.get('tax_amount', 0) for inv in invoice_data)
            
            states = set(inv.get('state_code') for inv in invoice_data if inv.get('state_code'))
            
            prompt = f"""
Analyze this GST filing data and provide actionable insights:

- Total Invoices: {total_invoices}
- Total Taxable Value: ₹{total_taxable:.2f}
- Total Tax: ₹{total_tax:.2f}
- States Covered: {len(states)} states

Provide insights on:
1. Overall data quality
2. Any red flags or compliance risks
3. Optimization opportunities
4. Filing recommendations

Return concise JSON:
{{
    "data_quality_score": 85,
    "key_insights": ["insight1", "insight2", "insight3"],
    "risks": ["risk1"],
    "recommendations": ["rec1", "rec2"]
}}
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            try:
                insights = json.loads(response_text)
                return insights
            except:
                return {
                    "key_insights": [response.text[:200]],
                    "note": "Text-based analysis"
                }
        
        except Exception as e:
            logger.error(f"Gemini insights error: {str(e)}")
            return {
                "key_insights": ["AI analysis unavailable"],
                "error": str(e)
            }


# Export singleton instance
gemini_service = GeminiService()
