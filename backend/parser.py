import io
import zipfile
from typing import List, Dict, BinaryIO, Tuple
import pandas as pd
from models import FileType, FileInfo, InvoiceLine
from utils import (
    detect_file_type,
    normalize_state_to_code,
    compute_tax_split,
    clean_numeric_value,
    validate_gst_rate
)


class FileParser:
    """Parse uploaded Excel/CSV files from Meesho exports"""
    
    def __init__(self, seller_state_code: str = "27"):  # Default: Maharashtra
        self.seller_state_code = seller_state_code
    
    def extract_files_from_zip(self, zip_content: bytes) -> List[Tuple[str, bytes]]:
        """Extract all Excel/CSV files from ZIP"""
        files = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                for filename in zf.namelist():
                    # Skip directories and hidden files
                    if filename.endswith('/') or filename.startswith('__MACOSX') or filename.startswith('.'):
                        continue
                    
                    # Only process Excel and CSV files
                    if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                        file_content = zf.read(filename)
                        files.append((filename, file_content))
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file")
        
        return files
    
    def read_excel_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """Read Excel or CSV file into DataFrame"""
        try:
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            
            return df
        except Exception as e:
            raise ValueError(f"Error reading file {filename}: {str(e)}")
    
    def detect_and_classify_files(self, files: List[Tuple[str, bytes]]) -> List[Dict]:
        """Detect file types and extract basic info"""
        classified_files = []
        
        for filename, content in files:
            try:
                df = self.read_excel_file(content, filename)
                columns = df.columns.tolist()
                
                file_type = detect_file_type(filename, columns)
                
                file_info = {
                    "filename": filename,
                    "file_type": file_type.value,
                    "detected": file_type != FileType.UNKNOWN,
                    "row_count": len(df),
                    "columns": columns,
                    "content": content
                }
                
                classified_files.append(file_info)
            except Exception as e:
                classified_files.append({
                    "filename": filename,
                    "file_type": FileType.UNKNOWN.value,
                    "detected": False,
                    "error": str(e)
                })
        
        return classified_files
    
    def parse_tcs_sales(self, df: pd.DataFrame, upload_id: str, is_return: bool = False) -> List[InvoiceLine]:
        """Parse TCS sales or sales return file"""
        invoice_lines = []
        
        # Expected columns (case-insensitive matching)
        required_cols = {
            'gst_rate': None,
            'total_taxable_sale_value': None,
            'end_customer_state_new': None
        }
        
        # Find actual column names (case-insensitive)
        for col in df.columns:
            col_lower = col.lower().strip()
            for req_col in required_cols.keys():
                if req_col.lower().replace('_', '') in col_lower.replace('_', ''):
                    required_cols[req_col] = col
                    break
        
        # Check if all required columns found
        missing_cols = [k for k, v in required_cols.items() if v is None]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Parse each row
        for idx, row in df.iterrows():
            try:
                # Extract values
                gst_rate = clean_numeric_value(row.get(required_cols['gst_rate']))
                taxable_value = clean_numeric_value(row.get(required_cols['total_taxable_sale_value']))
                state_name = str(row.get(required_cols['end_customer_state_new'], '')).strip()
                
                # Skip rows with missing critical data
                if gst_rate is None or taxable_value is None or not state_name:
                    continue
                
                # Validate GST rate
                if not validate_gst_rate(gst_rate):
                    continue
                
                # Normalize state
                state_code = normalize_state_to_code(state_name)
                if not state_code:
                    continue
                
                # Apply negative for returns
                if is_return:
                    taxable_value = -abs(taxable_value)
                
                # Compute tax split
                tax_split = compute_tax_split(
                    abs(taxable_value),
                    gst_rate,
                    self.seller_state_code,
                    state_code
                )
                
                # Adjust signs for returns
                if is_return:
                    tax_split['tax_amount'] = -abs(tax_split['tax_amount'])
                    tax_split['cgst_amount'] = -abs(tax_split['cgst_amount'])
                    tax_split['sgst_amount'] = -abs(tax_split['sgst_amount'])
                    tax_split['igst_amount'] = -abs(tax_split['igst_amount'])
                
                # Create invoice line
                invoice_line = InvoiceLine(
                    upload_id=upload_id,
                    file_type=FileType.TCS_SALES_RETURN if is_return else FileType.TCS_SALES,
                    gst_rate=gst_rate,
                    total_taxable_sale_value=taxable_value,
                    end_customer_state_new=state_name,
                    state_code=state_code,
                    is_return=is_return,
                    taxable_value=taxable_value,
                    tax_amount=tax_split['tax_amount'],
                    cgst_amount=tax_split['cgst_amount'],
                    sgst_amount=tax_split['sgst_amount'],
                    igst_amount=tax_split['igst_amount'],
                    is_intra_state=tax_split['is_intra_state'],
                    raw_data=row.to_dict()
                )
                
                invoice_lines.append(invoice_line)
                
            except Exception as e:
                # Log error but continue processing
                continue
        
        return invoice_lines
    
    def parse_tax_invoice(self, df: pd.DataFrame, upload_id: str) -> List[InvoiceLine]:
        """Parse tax invoice details file"""
        invoice_lines = []
        
        # Expected columns (flexible matching)
        type_col = None
        invoice_no_col = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'type' in col_lower and type_col is None:
                type_col = col
            if 'invoice' in col_lower and 'no' in col_lower and invoice_no_col is None:
                invoice_no_col = col
        
        if not type_col or not invoice_no_col:
            raise ValueError("Missing required columns: Type or Invoice No.")
        
        # Parse each row
        for idx, row in df.iterrows():
            try:
                invoice_type = str(row.get(type_col, '')).strip()
                invoice_no = str(row.get(invoice_no_col, '')).strip()
                
                if not invoice_type or not invoice_no:
                    continue
                
                # Create invoice line for serial tracking
                invoice_line = InvoiceLine(
                    upload_id=upload_id,
                    file_type=FileType.TAX_INVOICE,
                    invoice_type=invoice_type,
                    invoice_no=invoice_no,
                    raw_data=row.to_dict()
                )
                
                invoice_lines.append(invoice_line)
                
            except Exception as e:
                continue
        
        return invoice_lines
    
    def parse_file(self, file_content: bytes, filename: str, file_type: FileType, upload_id: str) -> List[InvoiceLine]:
        """Parse a single file based on its type"""
        df = self.read_excel_file(file_content, filename)
        
        if file_type == FileType.TCS_SALES:
            return self.parse_tcs_sales(df, upload_id, is_return=False)
        elif file_type == FileType.TCS_SALES_RETURN:
            return self.parse_tcs_sales(df, upload_id, is_return=True)
        elif file_type == FileType.TAX_INVOICE:
            return self.parse_tax_invoice(df, upload_id)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
