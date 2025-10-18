import React, { useState, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, FileText, Download, AlertCircle, Loader2, CheckCircle, Eye, ChevronDown, ChevronUp, X, Sparkles, Database, Zap } from "lucide-react";
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
          headers: { "Content-Type": "multipart/form-data" }
        }
      );

      const data = response.data;
      setUploadId(data.upload_id);
      setUploadDetails({ files: data.files });

      // Auto-process
      await handleProcess(data.upload_id);
      
    } catch (error) {
      setErrors([error.response?.data?.detail || error.message || "Upload failed"]);
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
      setAiInsights(response.data.ai_insights);
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
      
      setGstrData(data);
      
      if (data.validation_warnings && data.validation_warnings.length > 0) {
        setWarnings(data.validation_warnings);
      }

      if (data.ai_insights) {
        setAiInsights(data.ai_insights);
      }
      
    } catch (error) {
      setErrors([error.response?.data?.detail || error.message || "Generation failed"]);
    }
  };

  const downloadJSON = (data, filename) => {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
                <Sparkles className="w-3 h-3" />
                Gemini AI
              </Badge>
              <Badge variant="outline" className="gap-1 border-blue-500/30 text-blue-300 bg-blue-950/30">
                <Database className="w-3 h-3" />
                Supabase
              </Badge>
              <Badge variant="outline" className="gap-1 border-green-500/30 text-green-300 bg-green-950/30">
                <Zap className="w-3 h-3" />
                E-Commerce
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 sm:py-8 max-w-6xl">
        
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
              <Sparkles className="h-4 w-4 text-blue-400" />
              <AlertTitle className="text-blue-300">E-Commerce Note</AlertTitle>
              <AlertDescription className="text-blue-200 text-sm">
                Meesho acts as an e-commerce operator (ECO). Your sales will be reported under Meesho's GSTIN ({MEESHO_GSTIN}) as per GST regulations.
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

        {/* Preview Data */}
        {previewData && previewData.summary && (
          <Card className="mb-6 shadow-2xl border border-gray-800 bg-gray-900/50 backdrop-blur">
            <CardHeader className="bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border-b border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg sm:text-xl text-gray-100">Data Summary</CardTitle>
                  <CardDescription className="text-gray-400">Overview of processed transactions</CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPreview(!showPreview)}
                  className="text-gray-400 hover:text-gray-200"
                >
                  {showPreview ? <ChevronUp /> : <ChevronDown />}
                </Button>
              </div>
            </CardHeader>
            {showPreview && (
              <CardContent className="pt-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="p-4 bg-gradient-to-br from-purple-900/50 to-purple-800/30 rounded-lg border border-purple-700/30">
                    <p className="text-xs sm:text-sm text-purple-300 font-medium">Transactions</p>
                    <p className="text-xl sm:text-2xl font-bold text-purple-100">{previewData.summary.total_transactions}</p>
                  </div>
                  <div className="p-4 bg-gradient-to-br from-blue-900/50 to-blue-800/30 rounded-lg border border-blue-700/30">
                    <p className="text-xs sm:text-sm text-blue-300 font-medium">Taxable Value</p>
                    <p className="text-xl sm:text-2xl font-bold text-blue-100">₹{previewData.summary.total_taxable_value?.toLocaleString()}</p>
                  </div>
                  <div className="p-4 bg-gradient-to-br from-green-900/50 to-green-800/30 rounded-lg border border-green-700/30">
                    <p className="text-xs sm:text-sm text-green-300 font-medium">Total Tax</p>
                    <p className="text-xl sm:text-2xl font-bold text-green-100">₹{previewData.summary.total_tax?.toLocaleString()}</p>
                  </div>
                  <div className="p-4 bg-gradient-to-br from-orange-900/50 to-orange-800/30 rounded-lg border border-orange-700/30">
                    <p className="text-xs sm:text-sm text-orange-300 font-medium">States</p>
                    <p className="text-xl sm:text-2xl font-bold text-orange-100">{previewData.summary.unique_states}</p>
                  </div>
                </div>

                {/* AI Insights */}
                {aiInsights && aiInsights.key_insights && (
                  <div className="mb-6 p-4 bg-gradient-to-r from-purple-950/50 to-blue-950/50 rounded-lg border border-purple-700/30">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-5 h-5 text-purple-400" />
                      <h3 className="font-semibold text-purple-200">AI Insights</h3>
                    </div>
                    <ul className="space-y-2">
                      {aiInsights.key_insights.map((insight, index) => (
                        <li key={index} className="text-sm text-purple-300 flex items-start gap-2">
                          <span className="text-purple-400 mt-1">•</span>
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* State Breakdown */}
                {previewData.breakdown?.by_state_and_rate && previewData.breakdown.by_state_and_rate.length > 0 && (
                  <div className="mb-4">
                    <Button
                      variant="ghost"
                      onClick={() => toggleSection('stateBreakdown')}
                      className="w-full justify-between p-4 hover:bg-gray-800/50 text-gray-300"
                    >
                      <span className="font-medium">State-wise & Rate-wise Breakdown</span>
                      {expandedSections.stateBreakdown ? <ChevronUp /> : <ChevronDown />}
                    </Button>
                    {expandedSections.stateBreakdown && (
                      <div className="overflow-x-auto mt-2">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-800 border-b border-gray-700">
                            <tr>
                              <th className="p-3 text-left text-gray-300">State</th>
                              <th className="p-3 text-left text-gray-300">GST Rate</th>
                              <th className="p-3 text-right text-gray-300">Count</th>
                              <th className="p-3 text-right text-gray-300">Taxable Value</th>
                              <th className="p-3 text-right text-gray-300">Tax Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {previewData.breakdown.by_state_and_rate.map((item, index) => (
                              <tr key={index} className="border-b border-gray-800 hover:bg-gray-800/30">
                                <td className="p-3 text-gray-300">{item.state_name || item.state_code}</td>
                                <td className="p-3 text-gray-300">{item.gst_rate}%</td>
                                <td className="p-3 text-right text-gray-300">{item.count}</td>
                                <td className="p-3 text-right text-gray-300">₹{item.taxable_value?.toFixed(2)}</td>
                                <td className="p-3 text-right text-gray-300">₹{item.tax_amount?.toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        )}

        {/* GSTR Download */}
        {gstrData && (
          <Card className="mb-6 shadow-lg border-0">
            <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50">
              <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
                <CheckCircle className="w-5 h-5 text-green-600" />
                GSTR Files Ready
              </CardTitle>
              <CardDescription>Download your GST return JSON files</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Button
                  onClick={() => downloadJSON(gstrData.gstr1b, `GSTR1B_${filingPeriod}.json`)}
                  className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download GSTR-1B
                </Button>
                <Button
                  onClick={() => downloadJSON(gstrData.gstr3b, `GSTR3B_${filingPeriod}.json`)}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download GSTR-3B
                </Button>
              </div>

              {/* Summary Preview */}
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-3 text-sm">Summary</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-gray-600">GSTR-1B Tables</p>
                    <p className="font-medium">Table 7: {gstrData.gstr1b?.table7?.length || 0} entries</p>
                    <p className="font-medium">Table 13: {gstrData.gstr1b?.table13?.length || 0} entries</p>
                    <p className="font-medium">Table 14: {gstrData.gstr1b?.table14?.length || 0} entries</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Total Tax</p>
                    <p className="font-medium">
                      CGST: ₹{previewData?.summary?.total_cgst?.toFixed(2) || '0.00'}
                    </p>
                    <p className="font-medium">
                      SGST: ₹{previewData?.summary?.total_sgst?.toFixed(2) || '0.00'}
                    </p>
                    <p className="font-medium">
                      IGST: ₹{previewData?.summary?.total_igst?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12 py-6">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm text-gray-600">
            Made with <span className="text-red-500">♥</span> using Emergent
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
