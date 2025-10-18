import React, { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, FileText, Download, AlertCircle, Loader2, Info, CheckCircle, Eye, ChevronDown, ChevronUp, X, Sparkles, Brain, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

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
  const [showPreview, setShowPreview] = useState(false);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [aiInsights, setAiInsights] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    stateBreakdown: false,
    docBreakdown: false,
    auditLog: false,
    aiInsights: false
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
    setAiInsights(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await axios.post(
        `${API}/upload?seller_state_code=${stateCode}&gstin=${gstin}&filing_period=${filingPeriod}`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setUploadId(response.data.upload_id);
      setUploadDetails({
        files: response.data.files,
        message: response.data.message
      });
      
      // Auto-process after upload
      await handleProcess(response.data.upload_id);
    } catch (error) {
      console.error("Upload error:", error);
      setErrors([error.response?.data?.detail || "Upload failed"]);
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async (id) => {
    const processId = id || uploadId;
    if (!processId) return;

    setProcessing(true);
    setErrors([]);

    try {
      const response = await axios.post(`${API}/process/${processId}`);
      
      if (response.data.errors && response.data.errors.length > 0) {
        setErrors(response.data.errors);
      }
      
      // Auto-generate after processing
      await handleGenerate(processId);
    } catch (error) {
      console.error("Processing error:", error);
      setErrors([error.response?.data?.detail || "Processing failed"]);
    } finally {
      setProcessing(false);
    }
  };

  const handleGenerate = async (id) => {
    const generateId = id || uploadId;
    if (!generateId) return;

    try {
      const response = await axios.post(`${API}/generate/${generateId}`);
      setGstrData(response.data);
      setWarnings(response.data.validation_warnings || []);
      setAiInsights(response.data.ai_insights || null);
      
      // Fetch preview data
      await fetchPreviewData(generateId);
    } catch (error) {
      console.error("Generation error:", error);
      setErrors([error.response?.data?.detail || "Generation failed"]);
    }
  };

  const fetchPreviewData = async (id) => {
    try {
      const response = await axios.get(`${API}/preview/${id}`);
      setPreviewData(response.data);
    } catch (error) {
      console.error("Failed to fetch preview data:", error);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleDownload = (type) => {
    if (!gstrData) {
      console.error("No GSTR data available for download");
      setErrors(["No data available for download. Please generate GSTR files first."]);
      return;
    }

    try {
      const data = type === "gstr1b" ? gstrData.gstr1b : gstrData.gstr3b;
      
      if (!data) {
        console.error(`No ${type} data available`);
        setErrors([`No ${type.toUpperCase()} data available`]);
        return;
      }

      console.log(`Downloading ${type}...`, data);
      
      const jsonString = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_${gstin}_${filingPeriod}.json`;
      a.style.display = "none";
      
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log(`${type} downloaded successfully`);
      }, 100);
      
    } catch (error) {
      console.error("Download error:", error);
      setErrors([`Failed to download ${type.toUpperCase()}: ${error.message}`]);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-10 animate-fade-in">
          <div className="inline-flex items-center gap-2 mb-4 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full shadow-sm">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <span className="text-sm font-medium text-purple-600">AI-Powered GST Filing</span>
          </div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-3">
            GST Filing Automation
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Upload Meesho exports and generate GSTR-1B & GSTR-3B with AI-powered validation
          </p>
          <div className="mt-3 flex items-center justify-center gap-4 flex-wrap">
            <Badge variant="secondary" className="flex items-center gap-1">
              <Brain className="h-3 w-3" />
              Gemini AI
            </Badge>
            <Badge variant="secondary">Supabase Database</Badge>
            <Badge variant="secondary">E-Commerce: Meesho</Badge>
          </div>
        </div>

        {/* Info Alert */}
        <Alert className="mb-8 border-blue-200 bg-gradient-to-r from-blue-50 to-cyan-50 shadow-sm">
          <Info className="h-5 w-5 text-blue-600" />
          <AlertTitle className="text-blue-900 font-semibold">How it works</AlertTitle>
          <AlertDescription className="text-blue-800">
            <ol className="list-decimal list-inside space-y-2 mt-3">
              <li>Enter your business GSTIN and State Code (required for tax calculations)</li>
              <li>Upload Meesho export files or ZIP archive</li>
              <li>AI validates invoice sequences and GST calculations</li>
              <li>Download portal-ready GSTR-1B and GSTR-3B JSON files</li>
            </ol>
          </AlertDescription>
        </Alert>

        {/* Main Form */}
        <Card className="mb-8 shadow-lg border-2 border-white/50 backdrop-blur-sm">
          <CardHeader className="bg-gradient-to-r from-indigo-50 to-purple-50">
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-600" />
              Your GST Details
            </CardTitle>
            <CardDescription>Required information for GST filing and tax calculations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            <div className="grid md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <Label htmlFor="gstin" className="text-sm font-medium flex items-center gap-2">
                  Your Business GSTIN *
                </Label>
                <Input
                  data-testid="gstin-input"
                  id="gstin"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="27AABCE1234F1Z5"
                  className="font-mono border-2 focus:border-indigo-500 transition-colors"
                  maxLength={15}
                />
                <p className="text-xs text-slate-500">
                  15-digit GST Identification Number
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="stateCode" className="text-sm font-medium flex items-center gap-2">
                  Your State Code *
                </Label>
                <Input
                  data-testid="state-code-input"
                  id="stateCode"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  placeholder="27"
                  className="border-2 focus:border-indigo-500 transition-colors"
                  maxLength={2}
                />
                <p className="text-xs text-slate-500">
                  First 2 digits of GSTIN (e.g., 27 for Maharashtra)
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="filingPeriod" className="text-sm font-medium flex items-center gap-2">
                  Filing Period
                </Label>
                <Input
                  data-testid="filing-period-input"
                  id="filingPeriod"
                  value={filingPeriod}
                  onChange={(e) => setFilingPeriod(e.target.value)}
                  placeholder="012025"
                  className="border-2 focus:border-indigo-500 transition-colors"
                  maxLength={6}
                />
                <p className="text-xs text-slate-500">
                  MMYYYY format (e.g., 012025 = January 2025)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Upload Card */}
        <Card className="mb-8 shadow-lg border-2 border-white/50">
          <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-purple-600" />
              Upload Meesho Export Files
            </CardTitle>
            <CardDescription>
              Upload individual Excel/CSV files or a ZIP archive
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              data-testid="file-upload-zone"
              className={`border-2 border-dashed rounded-xl p-10 text-center transition-all duration-300 ${
                isDragging
                  ? "border-purple-500 bg-purple-50 scale-105"
                  : "border-slate-300 bg-gradient-to-br from-white to-slate-50 hover:border-purple-300"
              }`}
            >
              <Upload className="mx-auto h-16 w-16 text-purple-400 mb-4" />
              <p className="text-lg text-slate-700 font-medium mb-2">
                Drag and drop files here
              </p>
              <p className="text-sm text-slate-500 mb-4">
                or click to browse • Supported: .xlsx, .xls, .csv, .zip
              </p>
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="fileInput"
                accept=".zip,.xlsx,.xls,.csv"
                data-testid="file-input"
              />
              <Button
                data-testid="select-files-button"
                onClick={() => document.getElementById("fileInput").click()}
                variant="outline"
                className="border-2 hover:border-purple-500 hover:bg-purple-50 transition-all"
              >
                <FileText className="mr-2 h-4 w-4" />
                Select Files
              </Button>
            </div>

            {files.length > 0 && (
              <div className="mt-6 animate-slide-up">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-lg">Selected Files ({files.length}):</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setFiles([])}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    data-testid="clear-all-files-button"
                  >
                    <X className="h-3 w-3 mr-1" />
                    Clear All
                  </Button>
                </div>
                <ul className="space-y-2">
                  {files.map((file, index) => (
                    <li key={index} className="flex items-center justify-between p-3 bg-white rounded-lg border-2 border-slate-100 hover:border-purple-200 transition-colors" data-testid={`file-item-${index}`}>
                      <div className="flex items-center gap-3 flex-1">
                        <FileText className="h-5 w-5 text-purple-500" />
                        <span className="text-sm text-slate-700 font-medium">{file.name}</span>
                        <span className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded">
                          {(file.size / 1024).toFixed(2)} KB
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 ml-2"
                        data-testid={`remove-file-${index}`}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Button
              data-testid="upload-generate-button"
              onClick={handleUpload}
              disabled={files.length === 0 || uploading || processing || !gstin.trim() || !stateCode.trim()}
              className="w-full mt-6 h-14 text-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all"
            >
              {uploading || processing ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  {uploading ? "Uploading..." : "Processing with AI..."}
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-5 w-5" />
                  Upload & Generate GSTR Files
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Errors */}
        {errors.length > 0 && (
          <Alert variant="destructive" className="mb-6 animate-slide-up" data-testid="error-alert">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Errors</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside space-y-1">
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Warnings */}
        {warnings.length > 0 && (
          <Alert className="mb-6 bg-amber-50 border-amber-200 animate-slide-up" data-testid="warning-alert">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertTitle className="text-amber-900">Validation Warnings</AlertTitle>
            <AlertDescription className="text-amber-800">
              <ul className="list-disc list-inside space-y-1">
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Upload Details */}
        {uploadDetails && (
          <Card className="mb-6 animate-slide-up shadow-lg" data-testid="upload-details-card">
            <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                File Detection Results
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="space-y-3">
                {uploadDetails.files?.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-4 bg-white rounded-lg border-2 border-green-100 hover:border-green-200 transition-colors">
                    <div className="flex items-center gap-3">
                      <FileText className="h-6 w-6 text-green-600" />
                      <div>
                        <p className="font-medium text-slate-900">{file.filename}</p>
                        <p className="text-sm text-slate-600">
                          Type: <span className="font-medium">{file.file_type.replace(/_/g, ' ').toUpperCase()}</span> • Rows: <span className="font-medium">{file.row_count}</span>
                        </p>
                      </div>
                    </div>
                    <Badge variant={file.detected ? "default" : "secondary"} className="text-sm">
                      {file.detected ? "✓ Detected" : "Unknown"}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* AI Insights Section */}
        {aiInsights && (
          <Card className="mb-6 border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-pink-50 animate-slide-up shadow-lg" data-testid="ai-insights-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-purple-900 flex items-center gap-2">
                    <Brain className="h-6 w-6 text-purple-600" />
                    AI-Powered Insights
                  </CardTitle>
                  <CardDescription className="text-purple-700">
                    Gemini AI analysis of your GST filing
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => toggleSection('aiInsights')}
                  className="border-purple-300 hover:bg-purple-100"
                >
                  {expandedSections.aiInsights ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {expandedSections.aiInsights ? "Hide" : "Show"} Details
                </Button>
              </div>
            </CardHeader>
            {expandedSections.aiInsights && (
              <CardContent>
                {/* Invoice Analysis */}
                {aiInsights.invoice_analysis && (
                  <div className="mb-4 p-4 bg-white rounded-lg border-2 border-purple-100">
                    <h4 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      Invoice Sequence Analysis
                    </h4>
                    {aiInsights.invoice_analysis.missing_invoices && aiInsights.invoice_analysis.missing_invoices.length > 0 && (
                      <div className="mb-3">
                        <p className="text-sm text-red-600 font-medium mb-1">
                          ⚠️ {aiInsights.invoice_analysis.missing_invoices.length} Missing Invoice(s) Detected:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {aiInsights.invoice_analysis.missing_invoices.slice(0, 10).map((inv, idx) => (
                            <Badge key={idx} variant="destructive" className="text-xs">{inv}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {aiInsights.invoice_analysis.recommendations && (
                      <div>
                        <p className="text-sm font-medium text-slate-700 mb-2">Recommendations:</p>
                        <ul className="list-disc list-inside text-sm text-slate-600 space-y-1">
                          {aiInsights.invoice_analysis.recommendations.map((rec, idx) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Calculation Validation */}
                {aiInsights.calculation_validation && (
                  <div className="p-4 bg-white rounded-lg border-2 border-purple-100">
                    <h4 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4" />
                      GST Calculation Validation
                    </h4>
                    <div className="mb-3">
                      <Badge 
                        variant={aiInsights.calculation_validation.validation_status === 'pass' ? 'default' : 'destructive'}
                        className="text-sm"
                      >
                        {aiInsights.calculation_validation.validation_status === 'pass' ? '✓' : '⚠️'} 
                        {' '}{aiInsights.calculation_validation.validation_status.toUpperCase()}
                      </Badge>
                    </div>
                    {aiInsights.calculation_validation.summary && (
                      <p className="text-sm text-slate-700">{aiInsights.calculation_validation.summary}</p>
                    )}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        )}

        {/* Data Preview Section - Keeping existing structure but with enhanced styling */}
        {previewData && (
          <Card className="mb-6 border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-cyan-50 animate-slide-up shadow-lg" data-testid="preview-data-card">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-blue-900 flex items-center gap-2">
                    <Eye className="h-5 w-5" />
                    Data Review & Breakdown
                  </CardTitle>
                  <CardDescription className="text-blue-700">
                    Review your processed data before downloading
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setShowPreview(!showPreview)}
                  className="border-blue-300 hover:bg-blue-100"
                >
                  {showPreview ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {showPreview ? "Hide" : "Show"} Details
                </Button>
              </div>
            </CardHeader>
            {showPreview && (
              <CardContent>
                {/* Summary Cards */}
                <div className="grid md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-white p-5 rounded-xl border-2 border-blue-100 shadow-sm hover:shadow-md transition-shadow">
                    <div className="text-sm text-slate-600 mb-1">Total Transactions</div>
                    <div className="text-3xl font-bold text-slate-900">
                      {previewData.summary?.total_transactions || 0}
                    </div>
                  </div>
                  <div className="bg-white p-5 rounded-xl border-2 border-green-100 shadow-sm hover:shadow-md transition-shadow">
                    <div className="text-sm text-slate-600 mb-1">Total Taxable Value</div>
                    <div className="text-3xl font-bold text-green-600">
                      ₹{(previewData.summary?.total_taxable_value || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-white p-5 rounded-xl border-2 border-blue-100 shadow-sm hover:shadow-md transition-shadow">
                    <div className="text-sm text-slate-600 mb-1">Total Tax</div>
                    <div className="text-3xl font-bold text-blue-600">
                      ₹{(previewData.summary?.total_tax || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-white p-5 rounded-xl border-2 border-purple-100 shadow-sm hover:shadow-md transition-shadow">
                    <div className="text-sm text-slate-600 mb-1">Unique States</div>
                    <div className="text-3xl font-bold text-purple-600">
                      {previewData.summary?.unique_states || 0}
                    </div>
                  </div>
                </div>

                {/* State-wise Breakdown */}
                <div className="mb-4">
                  <button
                    onClick={() => toggleSection('stateBreakdown')}
                    className="flex items-center justify-between w-full p-4 bg-white rounded-xl border-2 border-blue-100 hover:bg-blue-50 transition-all shadow-sm hover:shadow-md"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <span className="font-semibold text-slate-900">State-wise & Rate-wise Breakdown (Table 7)</span>
                    </div>
                    {expandedSections.stateBreakdown ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.stateBreakdown && (
                    <div className="mt-2 bg-white p-5 rounded-xl border-2 border-blue-100 shadow-sm">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b-2 border-slate-200">
                              <th className="text-left p-3 font-semibold text-slate-700">State</th>
                              <th className="text-left p-3 font-semibold text-slate-700">Code</th>
                              <th className="text-right p-3 font-semibold text-slate-700">GST Rate</th>
                              <th className="text-right p-3 font-semibold text-slate-700">Count</th>
                              <th className="text-right p-3 font-semibold text-slate-700">Taxable Value</th>
                              <th className="text-right p-3 font-semibold text-slate-700">CGST</th>
                              <th className="text-right p-3 font-semibold text-slate-700">SGST</th>
                              <th className="text-right p-3 font-semibold text-slate-700">IGST</th>
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.breakdown?.by_state_and_rate?.map((item, idx) => (
                              <tr key={idx} className="border-b border-slate-100 hover:bg-blue-50 transition-colors">
                                <td className="p-3">{item.state_name}</td>
                                <td className="p-3 font-mono text-sm">{item.state_code}</td>
                                <td className="p-3 text-right font-medium">{item.gst_rate}%</td>
                                <td className="p-3 text-right">{item.count}</td>
                                <td className="p-3 text-right font-medium text-green-700">₹{item.taxable_value.toFixed(2)}</td>
                                <td className="p-3 text-right text-blue-700">₹{item.cgst_amount.toFixed(2)}</td>
                                <td className="p-3 text-right text-blue-700">₹{item.sgst_amount.toFixed(2)}</td>
                                <td className="p-3 text-right text-purple-700">₹{item.igst_amount.toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>

                {/* Document Type Breakdown */}
                <div className="mb-4">
                  <button
                    onClick={() => toggleSection('docBreakdown')}
                    className="flex items-center justify-between w-full p-4 bg-white rounded-xl border-2 border-blue-100 hover:bg-blue-50 transition-all shadow-sm hover:shadow-md"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      <span className="font-semibold text-slate-900">Document Issued Breakdown (Table 13)</span>
                    </div>
                    {expandedSections.docBreakdown ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.docBreakdown && (
                    <div className="mt-2 bg-white p-5 rounded-xl border-2 border-blue-100 shadow-sm">
                      <div className="space-y-3">
                        {previewData.breakdown?.by_document_type?.map((item, idx) => (
                          <div key={idx} className="p-4 bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg border border-slate-200">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-slate-900">{item.type}</span>
                              <Badge className="bg-blue-100 text-blue-700">{item.count} documents</Badge>
                            </div>
                            <div className="text-xs text-slate-600">
                              Invoice Numbers: {item.invoice_numbers.slice(0, 5).join(", ")}
                              {item.invoice_numbers.length > 5 && ` ... +${item.invoice_numbers.length - 5} more`}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Audit Log */}
                <div>
                  <button
                    onClick={() => toggleSection('auditLog')}
                    className="flex items-center justify-between w-full p-4 bg-white rounded-xl border-2 border-blue-100 hover:bg-blue-50 transition-all shadow-sm hover:shadow-md"
                  >
                    <div className="flex items-center gap-2">
                      <Info className="h-5 w-5 text-purple-600" />
                      <span className="font-semibold text-slate-900">Processing Audit Log</span>
                    </div>
                    {expandedSections.auditLog ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.auditLog && (
                    <div className="mt-2 bg-white p-5 rounded-xl border-2 border-blue-100 shadow-sm">
                      <ul className="space-y-2 text-sm">
                        {previewData.audit_log?.map((log, idx) => (
                          <li key={idx} className="flex items-start gap-3 p-2 hover:bg-slate-50 rounded transition-colors">
                            <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                            <span className="text-slate-700">{log}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {/* GSTR Download */}
        {gstrData && (
          <Card className="mb-6 border-2 border-green-300 bg-gradient-to-br from-green-50 to-emerald-50 animate-slide-up shadow-xl" data-testid="gstr-download-card">
            <CardHeader>
              <CardTitle className="text-green-900 flex items-center gap-2 text-2xl">
                <CheckCircle className="h-6 w-6 text-green-600" />
                ✓ GSTR Files Ready for Download
              </CardTitle>
              <CardDescription className="text-green-700 text-base">
                Your portal-ready JSON files are generated and validated
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <Button
                  data-testid="download-gstr1b-button"
                  onClick={() => handleDownload("gstr1b")}
                  className="w-full h-24 text-xl bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-lg hover:shadow-2xl transition-all transform hover:scale-105"
                >
                  <Download className="mr-3 h-6 w-6" />
                  Download GSTR-1B
                </Button>
                <Button
                  data-testid="download-gstr3b-button"
                  onClick={() => handleDownload("gstr3b")}
                  className="w-full h-24 text-xl bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 shadow-lg hover:shadow-2xl transition-all transform hover:scale-105"
                >
                  <Download className="mr-3 h-6 w-6" />
                  Download GSTR-3B
                </Button>
              </div>

              {/* Preview Summary */}
              <div className="space-y-4">
                <div className="p-6 bg-white rounded-xl border-2 border-green-200 shadow-sm">
                  <h4 className="font-semibold mb-4 text-slate-900 text-lg">GSTR-1B Summary</h4>
                  <div className="grid md:grid-cols-3 gap-6 text-sm">
                    <div className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg">
                      <div className="text-slate-600 mb-1">Table 7 (B2C Others)</div>
                      <div className="text-2xl font-bold text-slate-900">
                        {gstrData.gstr1b?.table7?.length || 0} entries
                      </div>
                    </div>
                    <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg">
                      <div className="text-slate-600 mb-1">Table 13 (Documents)</div>
                      <div className="text-2xl font-bold text-slate-900">
                        {gstrData.gstr1b?.table13?.length || 0} ranges
                      </div>
                    </div>
                    <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg">
                      <div className="text-slate-600 mb-1">Table 14 (ECO Supplies)</div>
                      <div className="text-2xl font-bold text-green-700">
                        ₹{gstrData.gstr1b?.table14?.[0]?.txval?.toFixed(2) || 0}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-white rounded-xl border-2 border-green-200 shadow-sm">
                  <h4 className="font-semibold mb-4 text-slate-900 text-lg">GSTR-3B Summary</h4>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg">
                      <h5 className="text-sm font-medium text-slate-700 mb-3">Section 3.1.1(ii) - ECO Supplies</h5>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-600">Taxable Value:</span>
                          <span className="font-semibold text-green-700">₹{gstrData.gstr3b?.section_311?.txval?.toFixed(2) || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-600">IGST:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_311?.iamt?.toFixed(2) || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-600">CGST:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_311?.camt?.toFixed(2) || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-600">SGST:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_311?.samt?.toFixed(2) || 0}</span>
                        </div>
                      </div>
                    </div>
                    <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg">
                      <h5 className="text-sm font-medium text-slate-700 mb-3">Section 3.2 - Inter-State</h5>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-600">Taxable Value:</span>
                          <span className="font-semibold text-purple-700">₹{gstrData.gstr3b?.section_32?.txval?.toFixed(2) || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-600">IGST:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_32?.iamt?.toFixed(2) || 0}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
      
      {/* Footer */}
      <div className="text-center py-8 text-sm text-slate-500">
        <p>Made with ❤️ using Emergent AI Platform</p>
        <p className="mt-1">Powered by Gemini AI & Supabase</p>
      </div>
    </div>
  );
}

export default App;