#!/usr/bin/env python3
"""
Backend API Testing for GST Filing Automation Application
Tests the complete file upload and GSTR generation flow
"""

import requests
import json
import sys
import os
from datetime import datetime

# Backend URL from frontend environment
BACKEND_URL = "https://typeerror-fix.preview.emergentagent.com/api"

class GSTBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_backend_health(self):
        """Test 1: Verify backend is running"""
        try:
            response = self.session.get(f"{BACKEND_URL}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "GST Filing Automation" in data["message"]:
                    self.log_test("Backend Health Check", True, 
                                f"Backend is running. Version: {data.get('version', 'unknown')}")
                    return True
                else:
                    self.log_test("Backend Health Check", False, 
                                "Backend responded but with unexpected format", data)
                    return False
            else:
                self.log_test("Backend Health Check", False, 
                            f"Backend returned status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Backend Health Check", False, 
                        f"Failed to connect to backend: {str(e)}")
            return False
    
    def test_list_uploads(self):
        """Test 2: Check existing uploads"""
        try:
            response = self.session.get(f"{BACKEND_URL}/uploads")
            
            if response.status_code == 200:
                data = response.json()
                uploads = data.get('uploads', [])
                
                self.log_test("List Uploads", True, 
                            f"Successfully retrieved {len(uploads)} uploads")
                
                # Return the uploads for further testing
                return uploads
            else:
                self.log_test("List Uploads", False, 
                            f"Failed to list uploads. Status: {response.status_code}", response.text)
                return []
                
        except Exception as e:
            self.log_test("List Uploads", False, 
                        f"Error listing uploads: {str(e)}")
            return []
    
    def test_upload_details(self, upload_id):
        """Test 3: Get upload details"""
        try:
            response = self.session.get(f"{BACKEND_URL}/upload/{upload_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['id', 'status', 'upload_date', 'files']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Upload Details", False, 
                                f"Missing required fields: {missing_fields}", data)
                    return None
                
                self.log_test("Upload Details", True, 
                            f"Upload {upload_id}: Status={data['status']}, Files={len(data.get('files', []))}")
                
                return data
            else:
                self.log_test("Upload Details", False, 
                            f"Failed to get upload details. Status: {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Upload Details", False, 
                        f"Error getting upload details: {str(e)}")
            return None
    
    def test_generate_gstr(self, upload_id):
        """Test 4: Generate GSTR files"""
        try:
            response = self.session.post(f"{BACKEND_URL}/generate/{upload_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for required response structure
                required_fields = ['upload_id', 'gstr1b', 'gstr3b']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Generate GSTR", False, 
                                f"Missing required fields in response: {missing_fields}", data)
                    return None
                
                # Check GSTR1B structure
                gstr1b = data.get('gstr1b', {})
                gstr1b_tables = ['table_7', 'table_13', 'table_14']
                gstr1b_missing = [table for table in gstr1b_tables if table not in gstr1b]
                
                # Check GSTR3B structure
                gstr3b = data.get('gstr3b', {})
                gstr3b_sections = ['section_3_1', 'section_3_2']
                gstr3b_missing = [section for section in gstr3b_sections if section not in gstr3b]
                
                if gstr1b_missing or gstr3b_missing:
                    self.log_test("Generate GSTR", False, 
                                f"Missing GSTR sections - GSTR1B: {gstr1b_missing}, GSTR3B: {gstr3b_missing}")
                    return None
                
                # Check for serialization errors
                try:
                    json.dumps(data)  # Test JSON serialization
                    self.log_test("Generate GSTR", True, 
                                f"Successfully generated GSTR files. Warnings: {len(data.get('validation_warnings', []))}")
                    return data
                except (TypeError, ValueError) as e:
                    self.log_test("Generate GSTR", False, 
                                f"JSON serialization error: {str(e)}")
                    return None
                
            elif response.status_code == 400:
                # Check if it's because upload needs processing first
                error_detail = response.json().get('detail', response.text)
                if "must be processed first" in error_detail:
                    self.log_test("Generate GSTR", False, 
                                f"Upload needs processing first: {error_detail}")
                    return "needs_processing"
                else:
                    self.log_test("Generate GSTR", False, 
                                f"Bad request: {error_detail}")
                    return None
            else:
                self.log_test("Generate GSTR", False, 
                            f"Failed to generate GSTR. Status: {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Generate GSTR", False, 
                        f"Error generating GSTR: {str(e)}")
            return None
    
    def test_process_upload(self, upload_id):
        """Test 5: Process upload if needed"""
        try:
            response = self.session.post(f"{BACKEND_URL}/process/{upload_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ['upload_id', 'status', 'invoice_lines_count']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Process Upload", False, 
                                f"Missing required fields: {missing_fields}", data)
                    return None
                
                self.log_test("Process Upload", True, 
                            f"Processing completed. Status: {data['status']}, Lines: {data['invoice_lines_count']}")
                return data
            else:
                self.log_test("Process Upload", False, 
                            f"Failed to process upload. Status: {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Process Upload", False, 
                        f"Error processing upload: {str(e)}")
            return None
    
    def test_downloads(self, upload_id):
        """Test 6: Check downloads availability"""
        try:
            response = self.session.get(f"{BACKEND_URL}/downloads/{upload_id}")
            
            if response.status_code == 200:
                data = response.json()
                exports = data.get('exports', [])
                
                self.log_test("Downloads Check", True, 
                            f"Found {len(exports)} available downloads")
                return exports
            elif response.status_code == 404:
                self.log_test("Downloads Check", True, 
                            "No downloads found yet (expected for new uploads)")
                return []
            else:
                self.log_test("Downloads Check", False, 
                            f"Failed to check downloads. Status: {response.status_code}", response.text)
                return []
                
        except Exception as e:
            self.log_test("Downloads Check", False, 
                        f"Error checking downloads: {str(e)}")
            return []
    
    def run_comprehensive_test(self):
        """Run complete test suite"""
        print("=" * 60)
        print("GST Filing Automation - Backend API Testing")
        print("=" * 60)
        
        # Test 1: Backend Health
        if not self.test_backend_health():
            print("\n❌ Backend is not accessible. Stopping tests.")
            return False
        
        # Test 2: List uploads
        uploads = self.test_list_uploads()
        
        if not uploads:
            print("\n⚠️  No existing uploads found. Cannot test upload processing flow.")
            print("   This is expected for a fresh installation.")
            return True
        
        # Test with the latest upload
        latest_upload = uploads[0]  # Assuming uploads are sorted by date
        upload_id = latest_upload.get('id')
        
        if not upload_id:
            print("\n❌ Upload ID not found in upload data")
            return False
        
        print(f"\n🔍 Testing with upload ID: {upload_id}")
        
        # Test 3: Upload details
        upload_details = self.test_upload_details(upload_id)
        if not upload_details:
            return False
        
        # Test 4: Check if processing is needed
        upload_status = upload_details.get('status')
        
        if upload_status != 'completed':
            print(f"\n📝 Upload status is '{upload_status}', attempting to process...")
            process_result = self.test_process_upload(upload_id)
            if not process_result:
                return False
        
        # Test 5: Generate GSTR files
        gstr_result = self.test_generate_gstr(upload_id)
        
        if gstr_result == "needs_processing":
            print("\n📝 Upload needs processing, attempting to process...")
            process_result = self.test_process_upload(upload_id)
            if process_result:
                # Retry generation after processing
                gstr_result = self.test_generate_gstr(upload_id)
        
        if not gstr_result:
            return False
        
        # Test 6: Check downloads
        self.test_downloads(upload_id)
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print(f"\n{'✅ ALL TESTS PASSED' if failed_tests == 0 else '❌ SOME TESTS FAILED'}")
        
        return failed_tests == 0

def main():
    """Main test execution"""
    tester = GSTBackendTester()
    
    try:
        success = tester.run_comprehensive_test()
        all_passed = tester.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()