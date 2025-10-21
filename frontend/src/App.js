import React, { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, FileText, Download, AlertCircle, Loader2, CheckCircle, Eye, ChevronDown, ChevronUp, X, Database, Zap, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import AdSpace from "./components/AdSpace";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Fixed values
const MEESHO_GSTIN = "07AARCM9332R1CQ";
const DEFAULT_FILING_PERIOD = "012025";

function App() {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [uploadDetails, setUploadDetails] = useState(null);
  const [gstrData, setGstrData] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [needsMapping, setNeedsMapping] = useState(false);
  const [mappingSuggestions, setMappingSuggestions] = useState(null);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [expandedSections, setExpandedSections] = useState({
    b2b: false,
    b2cl: false,
    b2cs: true,
    cdnr: false,
    cdnur: false,
    hsn: false,
    doc_iss: false
  });
  
  // User inputs
  const [gstin, setGstin] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [filingPeriod, setFilingPeriod] = useState(DEFAULT_FILING_PERIOD);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(droppedFiles);
  }, []);

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
  };

  const removeFile = (indexToRemove) => {
    setFiles(prevFiles => prevFiles.filter((_, index) => index !== indexToRemove));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setErrors(["Please select files to upload"]);
      return;
    }

    if (!gstin || gstin.trim().length < 15) {
      setErrors(["Please enter a valid 15-digit GSTIN"]);
      return;
    }

    if (!stateCode || stateCode.trim().length !== 2) {
      setErrors(["Please enter a valid 2-digit State Code"]);
      return;
    }

    setUploading(true);
    setErrors([]);
    setWarnings([]);
    setUploadId(null);
    setGstrData(null);
    setPreviewData(null);
    setNeedsMapping(false);
    setMappingSuggestions(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await axios.post(
        `${API}/upload?seller_state_code=${stateCode}&gstin=${gstin}&filing_period=${filingPeriod}`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" }
        }
      );

      const data = response.data;
      setUploadId(data.upload_id);
      setUploadDetails({ files: data.files });
      
      // Check if mapping needed
      if (data.needs_mapping) {
        setNeedsMapping(true);
        await fetchMappingSuggestions(data.upload_id);
      } else {
        // Auto-process
        await handleProcess(data.upload_id);
      }
      
    } catch (error) {
      setErrors([error.response?.data?.detail || error.message || "Upload failed"]);
    } finally {
      setUploading(false);
    }
  };

  const fetchMappingSuggestions = async (id) => {
    try {
      const response = await axios.get(`${API}/mapping/suggestions/${id}`);
      setMappingSuggestions(response.data);
    } catch (error) {
      console.error("Mapping suggestions error:", error);
      setErrors([error.response?.data?.detail || error.message || "Failed to fetch mapping suggestions"]);
    }
  };

  const handleApplyMapping = async () => {
    if (!uploadId || !mappingSuggestions) return;
    
    setProcessing(true);
    setErrors([]);
    
    try {
      // Use auto-suggested mappings
      const mappings = {};
      Object.keys(mappingSuggestions.suggestions).forEach(filename => {
        mappings[filename] = mappingSuggestions.suggestions[filename].mappings;
      });
      
      await axios.post(`${API}/mapping/apply/${uploadId}`, mappings);
      setNeedsMapping(false);
      setMappingSuggestions(null);
      
      // Continue with processing
      await handleProcess(uploadId);
      
    } catch (error) {
      setErrors([error.response?.data?.detail || error.message || "Failed to apply mapping"]);
      setProcessing(false);
    }
  };

  const handleProcess = async (id) => {
    const processId = id || uploadId;
    if (!processId) return;

    setProcessing(true);
    setErrors([]);

    try {
      const response = await axios.post(`${API}/process/${processId}`);
      const data = response.data;

      if (data.errors && data.errors.length > 0) {
        setErrors(data.errors);
      }

      // Fetch preview data
      await fetchPreviewData(processId);
      
      // Auto-generate GSTR
      await handleGenerate(processId);
      
    } catch (error) {
      setErrors([error.response?.data?.detail || error.message || "Processing failed"]);
    } finally {
      setProcessing(false);
    }
  };

  const fetchPreviewData = async (id) => {
    try {
      const response = await axios.get(`${API}/preview/${id}`);
      setPreviewData(response.data);
    } catch (error) {
      console.error("Preview fetch error:", error);
    }
  };

  const handleGenerate = async (id) => {
    const generateId = id || uploadId;
    if (!generateId) return;

    try {
      const response = await axios.post(`${API}/generate/${generateId}`);
      const data = response.data;
      
      console.log("Generated GSTR-1 data:", data);
      
      setGstrData(data);
      
      if (data.validation_warnings && data.validation_warnings.length > 0) {
        setWarnings(data.validation_warnings);
      }
      
    } catch (error) {
      console.error("Generation error:", error);
      setErrors([error.response?.data?.detail || error.message || "Generation failed"]);
    }
  };

  const downloadGSTR1 = () => {
    if (!uploadId) {
      setErrors(["No upload ID available for download"]);
      return;
    }
    
    try {
      // Use backend endpoint for reliable download
      const downloadUrl = `${API}/download/${uploadId}/gstr1`;
      
      // Create a temporary link and click it
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.style.display = "none";
      
      document.body.appendChild(link);
      link.click();
      
      setTimeout(() => {
        document.body.removeChild(link);
      }, 100);
      
    } catch (error) {
      console.error("Download error:", error);
      setErrors([`Download failed: ${error.message}`]);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-black">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50 shadow-xl">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center shadow-lg">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                  GST Filing Automation
                </h1>
                <p className="text-xs sm:text-sm text-gray-400">Powered by AI</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-4 flex-wrap justify-center">
              <Badge variant="outline" className="gap-1 border-purple-500/30 text-purple-300 bg-purple-950/30">
                <MapPin className="w-3 h-3" />
                Auto-Mapping
              </Badge>
              <Badge variant="outline" className="gap-1 border-blue-500/30 text-blue-300 bg-blue-950/30">
                <Database className="w-3 h-3" />
                Supabase
              </Badge>
              <Badge variant="outline" className="gap-1 border-green-500/30 text-green-300 bg-green-950/30">
                <Zap className="w-3 h-3" />
                GSTR-1
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Header Banner Ad */}
      <div className="container mx-auto px-4 py-4 max-w-7xl">
        <AdSpace adSlot="headerBanner" className="w-full" />
      </div>

      {/* Main Content with Sidebar Layout */}
      <div className="container mx-auto px-4 py-6 sm:py-8 max-w-7xl">
        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* Main Content Area */}
          <main className="flex-1 min-w-0">
        
        {/* Errors */}
        {errors.length > 0 && (
          <Alert variant="destructive" className="mb-6 bg-red-950/50 border-red-800">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <AlertTitle className="text-red-300">Error</AlertTitle>
            <AlertDescription className="text-red-200">
              <ul className="list-disc list-inside">
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <Alert className="mb-6 border-yellow-600/50 bg-yellow-950/30">
            <AlertCircle className="h-4 w-4 text-yellow-400" />
            <AlertTitle className="text-yellow-300">Validation Warnings</AlertTitle>
            <AlertDescription className="text-yellow-200">
              <ul className="list-disc list-inside">
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Configuration Form */}
        <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
          <CardHeader className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-b border-gray-800">
            <CardTitle className="text-lg sm:text-xl text-gray-100">Your GST Details</CardTitle>
            <CardDescription className="text-gray-400">Enter your business information for GST filing</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
              <div className="space-y-2">
                <Label htmlFor="gstin" className="text-sm font-medium text-gray-300">Business GSTIN *</Label>
                <Input
                  id="gstin"
                  placeholder="27AABCE1234F1Z5"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  maxLength={15}
                  className="font-mono bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500 focus:border-purple-500"
                />
                <p className="text-xs text-gray-500">15-digit GST identification number</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="stateCode" className="text-sm font-medium text-gray-300">State Code *</Label>
                <Input
                  id="stateCode"
                  placeholder="27"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  maxLength={2}
                  className="font-mono bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500 focus:border-purple-500"
                />
                <p className="text-xs text-gray-500">First 2 digits of GSTIN (e.g., 27 for MH)</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="filingPeriod" className="text-sm font-medium text-gray-300">Filing Period</Label>
                <Input
                  id="filingPeriod"
                  placeholder="012025"
                  value={filingPeriod}
                  onChange={(e) => setFilingPeriod(e.target.value)}
                  maxLength={6}
                  className="font-mono bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500 focus:border-purple-500"
                />
                <p className="text-xs text-gray-500">Format: MMYYYY (e.g., 012025 for Jan 2025)</p>
              </div>
            </div>

            <Alert className="mt-6 border-blue-600/50 bg-blue-950/30">
              <FileText className="h-4 w-4 text-blue-400" />
              <AlertTitle className="text-blue-300">Auto-Mapping Feature</AlertTitle>
              <AlertDescription className="text-blue-200 text-sm">
                Our smart system automatically maps your file headers to GSTR-1 fields. If manual mapping is needed, we'll guide you through the process.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* File Upload */}
        <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
          <CardHeader className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-b border-gray-800">
            <CardTitle className="text-lg sm:text-xl text-gray-100">Upload Meesho Export Files</CardTitle>
            <CardDescription className="text-gray-400">Upload Excel/CSV files or ZIP archive</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div
              className={`border-2 border-dashed rounded-lg p-8 sm:p-12 text-center transition-all ${
                isDragging 
                  ? "border-purple-500 bg-purple-950/30" 
                  : "border-gray-700 hover:border-purple-500/50 hover:bg-purple-950/20"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Upload className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 text-purple-400" />
              <p className="text-base sm:text-lg font-medium text-gray-300 mb-2">
                Drag and drop files here
              </p>
              <p className="text-sm text-gray-500 mb-4">or</p>
              <Button 
                variant="outline" 
                className="cursor-pointer bg-gray-800 border-gray-700 text-gray-200 hover:bg-purple-900/50 hover:border-purple-500"
                onClick={() => document.getElementById('file-upload').click()}
              >
                Select Files
              </Button>
              <input
                id="file-upload"
                type="file"
                multiple
                accept=".xlsx,.xls,.csv,.zip"
                onChange={handleFileSelect}
                className="hidden"
              />
              <p className="text-xs text-gray-600 mt-4">Supported: .xlsx, .xls, .csv, .zip</p>
            </div>

            {/* Selected Files */}
            {files.length > 0 && (
              <div className="mt-6 space-y-2">
                <p className="text-sm font-medium text-gray-300">Selected Files ({files.length})</p>
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <FileText className="w-5 h-5 text-purple-400 flex-shrink-0" />
                        <span className="text-sm truncate text-gray-300">{file.name}</span>
                        <span className="text-xs text-gray-500 flex-shrink-0">
                          {(file.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        className="flex-shrink-0 text-gray-400 hover:text-red-400 hover:bg-red-950/30"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>

                <Button
                  onClick={handleUpload}
                  disabled={uploading || processing}
                  className="w-full mt-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-lg"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : processing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Upload & Process
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* In-Content Ad 1 */}
        <AdSpace adSlot="inContent1" className="w-full mb-6" />

        {/* Upload Details */}
        {uploadDetails && uploadDetails.files && (
          <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
            <CardHeader className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border-b border-gray-800">
              <CardTitle className="flex items-center gap-2 text-lg sm:text-xl text-gray-100">
                <CheckCircle className="w-5 h-5 text-green-400" />
                Upload Successful
              </CardTitle>
              <CardDescription className="text-gray-400">Files detected and classified</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {uploadDetails.files.map((file, index) => (
                  <div key={index} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700 gap-3">
                    <div className="flex items-start sm:items-center gap-3 flex-1 min-w-0">
                      <FileText className="w-5 h-5 text-purple-400 flex-shrink-0 mt-1 sm:mt-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate text-gray-300">{file.filename}</p>
                        {file.row_count && (
                          <p className="text-xs text-gray-500">{file.row_count} rows</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge 
                        variant={file.detected ? "default" : "secondary"}
                        className={file.detected ? "bg-green-600 hover:bg-green-700" : "bg-gray-700"}
                      >
                        {file.file_type}
                      </Badge>
                      {file.detected && (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Mapping UI */}
        {needsMapping && mappingSuggestions && (
          <Card className="mb-6 shadow-2xl border border-yellow-600 bg-gray-900/50 backdrop-blur">
            <CardHeader className="bg-gradient-to-r from-yellow-900/30 to-orange-900/30 border-b border-yellow-800">
              <CardTitle className="flex items-center gap-2 text-lg sm:text-xl text-gray-100">
                <MapPin className="w-5 h-5 text-yellow-400" />
                Field Mapping Required
              </CardTitle>
              <CardDescription className="text-gray-400">
                We've auto-detected field mappings. Review and proceed.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {Object.keys(mappingSuggestions.suggestions).map((filename, fileIndex) => {
                const suggestion = mappingSuggestions.suggestions[filename];
                return (
                  <div key={fileIndex} className="mb-6 last:mb-0">
                    <h4 className="text-sm font-semibold text-gray-300 mb-3">{filename}</h4>
                    <div className="space-y-2">
                      {suggestion.mappings.map((mapping, mapIndex) => (
                        <div key={mapIndex} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-gray-400">{mapping.file_header}</span>
                            <span className="text-xs text-gray-600">→</span>
                            <span className="text-sm font-medium text-purple-300">{mapping.canonical_field}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                              {(mapping.confidence * 100).toFixed(0)}% {mapping.match_type}
                            </Badge>
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          </div>
                        </div>
                      ))}
                    </div>
                    {suggestion.suggested_section && (
                      <p className="text-xs text-gray-500 mt-2">
                        Suggested section: <span className="text-purple-400 font-medium">{suggestion.suggested_section.toUpperCase()}</span>
                      </p>
                    )}
                  </div>
                );
              })}
              <Button
                onClick={handleApplyMapping}
                disabled={processing}
                className="w-full mt-4 bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700 text-white shadow-lg"
              >
                {processing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Applying & Processing...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Apply Mapping & Continue
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Preview Data - GSTR-1 Sections */}
        {previewData && previewData.summary && (
          <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
            <CardHeader className="bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border-b border-gray-800">
              <CardTitle className="text-lg sm:text-xl text-gray-100">Data Summary</CardTitle>
              <CardDescription className="text-gray-400">Overview of processed transactions</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="p-4 bg-gradient-to-br from-purple-900/50 to-purple-800/30 rounded-lg border border-purple-700/30">
                  <p className="text-xs sm:text-sm text-purple-300 font-medium">Total Lines</p>
                  <p className="text-xl sm:text-2xl font-bold text-purple-100">{previewData.summary.total_lines}</p>
                </div>
                <div className="p-4 bg-gradient-to-br from-blue-900/50 to-blue-800/30 rounded-lg border border-blue-700/30">
                  <p className="text-xs sm:text-sm text-blue-300 font-medium">Taxable Value</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-100">₹{previewData.summary.total_taxable_value?.toFixed(2)}</p>
                </div>
                <div className="p-4 bg-gradient-to-br from-green-900/50 to-green-800/30 rounded-lg border border-green-700/30">
                  <p className="text-xs sm:text-sm text-green-300 font-medium">Total Tax</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-100">₹{previewData.summary.total_tax?.toFixed(2)}</p>
                </div>
                <div className="p-4 bg-gradient-to-br from-orange-900/50 to-orange-800/30 rounded-lg border border-orange-700/30">
                  <p className="text-xs sm:text-sm text-orange-300 font-medium">CGST</p>
                  <p className="text-xl sm:text-2xl font-bold text-orange-100">₹{previewData.summary.total_cgst?.toFixed(2)}</p>
                </div>
              </div>

              {/* GSTR-1 Sections Breakdown */}
              {previewData.section_breakdown && (
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-gray-300 mb-3">GSTR-1 Sections Breakdown</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {Object.entries(previewData.section_breakdown).map(([section, count]) => (
                      <div key={section} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                        <p className="text-xs text-gray-500 uppercase mb-1">{section}</p>
                        <p className="text-lg font-bold text-gray-200">{count} entries</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* In-Content Ad 2 */}
        <AdSpace adSlot="inContent2" className="w-full mb-6" />

        {/* GSTR-1 Download */}
        {gstrData && (
          <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
            <CardHeader className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border-b border-gray-800">
              <CardTitle className="flex items-center gap-2 text-lg sm:text-xl text-gray-100">
                <CheckCircle className="w-5 h-5 text-green-400" />
                GSTR-1 Ready for Download
              </CardTitle>
              <CardDescription className="text-gray-400">Your GSTR-1 JSON file is ready</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <Button
                onClick={downloadGSTR1}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg mb-6"
              >
                <Download className="w-4 h-4 mr-2" />
                Download GSTR-1 JSON
              </Button>

              {/* GSTR-1 Sections Summary */}
              <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                <h4 className="font-semibold mb-3 text-sm text-gray-300">GSTR-1 Sections Included</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500 text-xs">B2B (Registered)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.b2b?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">B2CL (Large)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.b2cl?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">B2CS (Small)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.b2cs?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">CDNR (Reg. Notes)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.cdnr?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">CDNUR (Unreg. Notes)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.cdnur?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">HSN Summary</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.hsn?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs">DOC_ISS (Table 13)</p>
                    <p className="font-medium text-gray-300">{gstrData.gstr1?.doc_iss?.length || 0} entries</p>
                  </div>
                </div>
                
                {/* Tax Summary */}
                <div className="mt-4 pt-4 border-t border-gray-700">
                  <p className="text-xs text-gray-500 mb-2">Tax Summary</p>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <p className="text-gray-500 text-xs">CGST</p>
                      <p className="font-medium text-gray-300">₹{previewData?.summary?.total_cgst?.toFixed(2) || '0.00'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs">SGST</p>
                      <p className="font-medium text-gray-300">₹{previewData?.summary?.total_sgst?.toFixed(2) || '0.00'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs">IGST</p>
                      <p className="font-medium text-gray-300">₹{previewData?.summary?.total_igst?.toFixed(2) || '0.00'}</p>
                    </div>
                  </div>
                </div>
                
                {/* Validation Status */}
                {gstrData.validation_warnings && gstrData.validation_warnings.length === 0 && (
                  <div className="mt-4 flex items-center gap-2 text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-sm">All validations passed</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
          </main>

          {/* Sidebar with Ads */}
          <aside className="lg:w-80 flex-shrink-0 space-y-6">
            {/* Sidebar Ad */}
            <div className="sticky top-24">
              <AdSpace adSlot="sidebar" className="w-full" />
            </div>
          </aside>

        </div>
      </div>

      {/* Footer Banner Ad */}
      <div className="container mx-auto px-4 py-4 max-w-7xl">
        <AdSpace adSlot="footerBanner" className="w-full" />
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 mt-12 py-6">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-gray-400">
            Made with <span className="text-red-500">♥</span> using Emergent
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
