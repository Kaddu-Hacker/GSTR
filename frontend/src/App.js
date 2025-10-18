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
    } catch (error) {
      setErrors([error.response?.data?.detail || "Generation failed"]);
    }
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
              <li>Enter your GSTIN and State Code</li>
              <li>Upload Meesho files: tcs_sales.xlsx, tcs_sales_return.xlsx, Tax_invoice_details.xlsx (or ZIP)</li>
              <li>Get portal-ready GSTR-1B (Tables 7, 13, 14) and GSTR-3B JSON files</li>
            </ol>
          </AlertDescription>
        </Alert>

        {/* Main Form */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Your GST Details</CardTitle>
            <CardDescription>Enter your business information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="gstin">Your GSTIN *</Label>
                <Input
                  id="gstin"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value.toUpperCase())}
                  placeholder="27AABCE1234F1Z5"
                  className="font-mono"
                />
              </div>
              <div>
                <Label htmlFor="stateCode">Your State Code *</Label>
                <Input
                  id="stateCode"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  placeholder="27"
                  maxLength={2}
                />
              </div>
              <div>
                <Label htmlFor="filingPeriod">Filing Period (MMYYYY)</Label>
                <Input
                  id="filingPeriod"
                  value={filingPeriod}
                  onChange={(e) => setFilingPeriod(e.target.value)}
                  placeholder="012025"
                  maxLength={6}
                />
              </div>
            </div>
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
                <h3 className="font-semibold mb-2">Selected Files:</h3>
                <ul className="space-y-1">
                  {files.map((file, index) => (
                    <li key={index} className="text-sm text-slate-600 flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      {file.name} ({(file.size / 1024).toFixed(2)} KB)
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
