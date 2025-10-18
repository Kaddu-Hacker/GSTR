import React, { useState, useCallback, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, FileText, Download, AlertCircle, Loader2, Info, CheckCircle, Eye, ChevronDown, ChevronUp } from "lucide-react";
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
  const [expandedSections, setExpandedSections] = useState({
    stateBreakdown: false,
    docBreakdown: false,
    auditLog: false
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

    if (!gstin || !stateCode) {
      setErrors(["Please enter your GSTIN and State Code"]);
      return;
    }

    setUploading(true);
    setErrors([]);
    setWarnings([]);
    setUploadId(null);
    setGstrData(null);

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
      
      // Fetch preview data
      await fetchPreviewData(generateId);
    } catch (error) {
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
    if (!gstrData) return;

    const data = type === "gstr1b" ? gstrData.gstr1b : gstrData.gstr3b;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${type}_${gstin}_${filingPeriod}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            GST Filing Automation for Meesho Sellers
          </h1>
          <p className="text-slate-600">
            Upload Meesho exports and generate GSTR-1B & GSTR-3B JSON files
          </p>
          <div className="mt-2 text-sm text-slate-500">
            E-Commerce Operator: Meesho (GSTIN: {MEESHO_GSTIN})
          </div>
        </div>

        {/* Info Alert */}
        <Alert className="mb-6 bg-blue-50 border-blue-200">
          <Info className="h-4 w-4 text-blue-600" />
          <AlertTitle className="text-blue-900">How it works</AlertTitle>
          <AlertDescription className="text-blue-800">
            <ol className="list-decimal list-inside space-y-1 mt-2">
              <li>Enter your business GSTIN and State Code (required for tax calculations)</li>
              <li>Upload Meesho export files: tcs_sales.xlsx, tcs_sales_return.xlsx, Tax_invoice_details.xlsx (or ZIP)</li>
              <li>Review the processed data breakdown before download</li>
              <li>Download portal-ready GSTR-1B (Tables 7, 13, 14) and GSTR-3B JSON files</li>
            </ol>
          </AlertDescription>
        </Alert>

        {/* Main Form */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Your GST Details</CardTitle>
            <CardDescription>Required information for GST filing and tax calculations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="gstin" className="flex items-center gap-2">
                  Your Business GSTIN *
                  <span className="text-xs text-slate-500 font-normal">(15-digit GST Identification Number)</span>
                </Label>
                <Input
                  id="gstin"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="27AABCE1234F1Z5"
                  className="font-mono"
                  maxLength={15}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Used in GSTR-1B and GSTR-3B as your business identifier
                </p>
              </div>
              <div>
                <Label htmlFor="stateCode" className="flex items-center gap-2">
                  Your State Code *
                  <span className="text-xs text-slate-500 font-normal">(First 2 digits of GSTIN)</span>
                </Label>
                <Input
                  id="stateCode"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  placeholder="27"
                  maxLength={2}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Used to determine intra-state (CGST+SGST) vs inter-state (IGST) transactions
                </p>
              </div>
              <div>
                <Label htmlFor="filingPeriod" className="flex items-center gap-2">
                  Filing Period
                  <span className="text-xs text-slate-500 font-normal">(MMYYYY format)</span>
                </Label>
                <Input
                  id="filingPeriod"
                  value={filingPeriod}
                  onChange={(e) => setFilingPeriod(e.target.value)}
                  placeholder="012025"
                  maxLength={6}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Tax period for which you're filing (e.g., 012025 = January 2025)
                </p>
              </div>
            </div>
            <Alert className="mt-4 bg-amber-50 border-amber-200">
              <AlertCircle className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-amber-900 text-sm">
                <strong>E-Commerce Operator (ECO):</strong> Meesho GSTIN ({MEESHO_GSTIN}) will be used for Table 14 reporting. 
                Your sales will be reported in both Table 7 (state-wise B2C) and Table 14 (ECO platform-wise) as per GST rules.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Upload Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Upload Meesho Export Files</CardTitle>
            <CardDescription>
              Upload individual Excel/CSV files or a ZIP archive containing all files
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging
                  ? "border-blue-500 bg-blue-50"
                  : "border-slate-300 bg-white"
              }`}
            >
              <Upload className="mx-auto h-12 w-12 text-slate-400 mb-4" />
              <p className="text-slate-600 mb-2">
                Drag and drop files here, or click to select
              </p>
              <p className="text-sm text-slate-500 mb-4">
                Supported: .xlsx, .xls, .csv, .zip
              </p>
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="fileInput"
                accept=".zip,.xlsx,.xls,.csv"
              />
              <Button
                onClick={() => document.getElementById("fileInput").click()}
                variant="outline"
              >
                Select Files
              </Button>
            </div>

            {files.length > 0 && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">Selected Files:</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setFiles([])}
                    className="text-red-600 hover:text-red-700"
                  >
                    Clear All
                  </Button>
                </div>
                <ul className="space-y-2">
                  {files.map((file, index) => (
                    <li key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded border">
                      <div className="flex items-center gap-2 flex-1">
                        <FileText className="h-4 w-4 text-slate-600" />
                        <span className="text-sm text-slate-700">{file.name}</span>
                        <span className="text-xs text-slate-500">({(file.size / 1024).toFixed(2)} KB)</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <span className="text-xs">Remove</span>
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading || processing || !gstin || !stateCode}
              className="w-full mt-4"
            >
              {uploading || processing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {uploading ? "Uploading..." : "Processing..."}
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload & Generate GSTR Files
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Errors */}
        {errors.length > 0 && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Errors</AlertTitle>
            <AlertDescription>
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
          <Alert className="mb-6 bg-yellow-50 border-yellow-200">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <AlertTitle className="text-yellow-900">Validation Warnings</AlertTitle>
            <AlertDescription className="text-yellow-800">
              <ul className="list-disc list-inside">
                {warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Upload Details */}
        {uploadDetails && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>File Detection Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {uploadDetails.files?.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-slate-600" />
                      <div>
                        <p className="font-medium">{file.filename}</p>
                        <p className="text-sm text-slate-600">
                          Type: {file.file_type.replace(/_/g, ' ').toUpperCase()} • Rows: {file.row_count}
                        </p>
                      </div>
                    </div>
                    <Badge variant={file.detected ? "default" : "secondary"}>
                      {file.detected ? "✓ Detected" : "Unknown"}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Data Review/Preview Section */}
        {previewData && (
          <Card className="mb-6 border-2 border-blue-200 bg-blue-50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-blue-900 flex items-center gap-2">
                    <Eye className="h-5 w-5" />
                    Data Review & Breakdown
                  </CardTitle>
                  <CardDescription className="text-blue-700">
                    Review your processed data before generating GSTR files
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setShowPreview(!showPreview)}
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
                  <div className="bg-white p-4 rounded-lg border">
                    <div className="text-sm text-slate-600">Total Transactions</div>
                    <div className="text-2xl font-bold text-slate-900">
                      {previewData.summary?.total_transactions || 0}
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border">
                    <div className="text-sm text-slate-600">Total Taxable Value</div>
                    <div className="text-2xl font-bold text-green-600">
                      ₹{(previewData.summary?.total_taxable_value || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border">
                    <div className="text-sm text-slate-600">Total Tax</div>
                    <div className="text-2xl font-bold text-blue-600">
                      ₹{(previewData.summary?.total_tax || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border">
                    <div className="text-sm text-slate-600">Unique States</div>
                    <div className="text-2xl font-bold text-purple-600">
                      {previewData.summary?.unique_states || 0}
                    </div>
                  </div>
                </div>

                {/* State-wise Breakdown */}
                <div className="mb-4">
                  <button
                    onClick={() => toggleSection('stateBreakdown')}
                    className="flex items-center justify-between w-full p-3 bg-white rounded-lg border hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="font-semibold">State-wise & Rate-wise Breakdown (Table 7)</span>
                    </div>
                    {expandedSections.stateBreakdown ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.stateBreakdown && (
                    <div className="mt-2 bg-white p-4 rounded-lg border">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b">
                              <th className="text-left p-2">State</th>
                              <th className="text-left p-2">State Code</th>
                              <th className="text-right p-2">GST Rate</th>
                              <th className="text-right p-2">Count</th>
                              <th className="text-right p-2">Taxable Value</th>
                              <th className="text-right p-2">CGST</th>
                              <th className="text-right p-2">SGST</th>
                              <th className="text-right p-2">IGST</th>
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.breakdown?.by_state_and_rate?.map((item, idx) => (
                              <tr key={idx} className="border-b hover:bg-slate-50">
                                <td className="p-2">{item.state_name}</td>
                                <td className="p-2 font-mono">{item.state_code}</td>
                                <td className="p-2 text-right">{item.gst_rate}%</td>
                                <td className="p-2 text-right">{item.count}</td>
                                <td className="p-2 text-right font-medium">₹{item.taxable_value.toFixed(2)}</td>
                                <td className="p-2 text-right">₹{item.cgst_amount.toFixed(2)}</td>
                                <td className="p-2 text-right">₹{item.sgst_amount.toFixed(2)}</td>
                                <td className="p-2 text-right">₹{item.igst_amount.toFixed(2)}</td>
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
                    className="flex items-center justify-between w-full p-3 bg-white rounded-lg border hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                      <span className="font-semibold">Document Issued Breakdown (Table 13)</span>
                    </div>
                    {expandedSections.docBreakdown ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.docBreakdown && (
                    <div className="mt-2 bg-white p-4 rounded-lg border">
                      <div className="space-y-3">
                        {previewData.breakdown?.by_document_type?.map((item, idx) => (
                          <div key={idx} className="p-3 bg-slate-50 rounded">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">{item.type}</span>
                              <Badge>{item.count} documents</Badge>
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
                    className="flex items-center justify-between w-full p-3 bg-white rounded-lg border hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Info className="h-4 w-4 text-purple-600" />
                      <span className="font-semibold">Processing Audit Log</span>
                    </div>
                    {expandedSections.auditLog ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {expandedSections.auditLog && (
                    <div className="mt-2 bg-white p-4 rounded-lg border">
                      <ul className="space-y-2 text-sm">
                        {previewData.audit_log?.map((log, idx) => (
                          <li key={idx} className="flex items-start gap-2">
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
          <Card className="mb-6 border-2 border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="text-green-900">✓ GSTR Files Ready</CardTitle>
              <CardDescription className="text-green-700">
                Your portal-ready JSON files are generated and ready for download
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4 mb-6">
                <Button
                  onClick={() => handleDownload("gstr1b")}
                  className="w-full h-20 text-lg bg-green-600 hover:bg-green-700"
                >
                  <Download className="mr-2 h-5 w-5" />
                  Download GSTR-1B
                </Button>
                <Button
                  onClick={() => handleDownload("gstr3b")}
                  className="w-full h-20 text-lg bg-green-600 hover:bg-green-700"
                >
                  <Download className="mr-2 h-5 w-5" />
                  Download GSTR-3B
                </Button>
              </div>

              {/* Preview Summary */}
              <div className="space-y-4">
                <div className="p-4 bg-white rounded-lg border">
                  <h4 className="font-semibold mb-3 text-slate-900">GSTR-1B Summary</h4>
                  <div className="grid md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-slate-600">Table 7 (B2C Others)</div>
                      <div className="text-lg font-bold text-slate-900">
                        {gstrData.gstr1b?.table7?.length || 0} entries
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-600">Table 13 (Documents)</div>
                      <div className="text-lg font-bold text-slate-900">
                        {gstrData.gstr1b?.table13?.length || 0} ranges
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-600">Table 14 (ECO Supplies)</div>
                      <div className="text-lg font-bold text-slate-900">
                        ₹{gstrData.gstr1b?.table14?.[0]?.txval?.toFixed(2) || 0}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-white rounded-lg border">
                  <h4 className="font-semibold mb-3 text-slate-900">GSTR-3B Summary</h4>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <h5 className="text-sm font-medium text-slate-700 mb-2">Section 3.1.1(ii) - ECO Supplies</h5>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-600">Taxable Value:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_311?.txval?.toFixed(2) || 0}</span>
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
                    <div>
                      <h5 className="text-sm font-medium text-slate-700 mb-2">Section 3.2 - Inter-State</h5>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-600">Taxable Value:</span>
                          <span className="font-semibold">₹{gstrData.gstr3b?.section_32?.txval?.toFixed(2) || 0}</span>
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
    </div>
  );
}

export default App;
