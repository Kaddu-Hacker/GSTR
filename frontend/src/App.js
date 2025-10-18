import React, { useState, useCallback, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, FileText, Download, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [uploadDetails, setUploadDetails] = useState(null);
  const [gstrData, setGstrData] = useState(null);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  
  // Form fields
  const [gstin, setGstin] = useState("27AABCE1234F1Z5");
  const [stateCode, setStateCode] = useState("27");
  const [filingPeriod, setFilingPeriod] = useState("012025");
  
  const [uploads, setUploads] = useState([]);

  // Load uploads on mount
  useEffect(() => {
    loadUploads();
  }, []);

  const loadUploads = async () => {
    try {
      const response = await axios.get(`${API}/uploads`);
      setUploads(response.data.uploads || []);
    } catch (e) {
      console.error("Error loading uploads:", e);
    }
  };

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
      
      // Reload uploads list
      await loadUploads();
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

  const loadUploadDetails = async (id) => {
    try {
      const response = await axios.get(`${API}/upload/${id}`);
      setUploadId(id);
      setUploadDetails(response.data);
      
      // Check if GSTR data exists
      if (response.data.exports && response.data.exports.length > 0) {
        const downloadsResponse = await axios.get(`${API}/downloads/${id}`);
        
        const gstr1bExport = downloadsResponse.data.exports.find(e => e.export_type === "GSTR1B");
        const gstr3bExport = downloadsResponse.data.exports.find(e => e.export_type === "GSTR3B");
        
        if (gstr1bExport && gstr3bExport) {
          setGstrData({
            upload_id: id,
            gstr1b: gstr1bExport.json_data,
            gstr3b: gstr3bExport.json_data,
            validation_warnings: gstr1bExport.validation_warnings
          });
          setWarnings(gstr1bExport.validation_warnings || []);
        }
      }
    } catch (error) {
      setErrors([error.response?.data?.detail || "Failed to load upload details"]);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            GST Filing Automation
          </h1>
          <p className="text-slate-600">
            Upload Meesho exports and generate GSTR-1B & GSTR-3B JSON files
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {/* Configuration Card */}
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle>Configuration</CardTitle>
              <CardDescription>Enter your GST details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="gstin">GSTIN</Label>
                <Input
                  id="gstin"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value)}
                  placeholder="27AABCE1234F1Z5"
                />
              </div>
              <div>
                <Label htmlFor="stateCode">State Code</Label>
                <Input
                  id="stateCode"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  placeholder="27"
                />
              </div>
              <div>
                <Label htmlFor="filingPeriod">Filing Period (MMYYYY)</Label>
                <Input
                  id="filingPeriod"
                  value={filingPeriod}
                  onChange={(e) => setFilingPeriod(e.target.value)}
                  placeholder="012025"
                />
              </div>
            </CardContent>
          </Card>

          {/* Upload Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Upload Files</CardTitle>
              <CardDescription>
                Upload Meesho export files (ZIP or individual Excel/CSV files)
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
                disabled={files.length === 0 || uploading || processing}
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
                    Upload & Process
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

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
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Validation Warnings</AlertTitle>
            <AlertDescription>
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
              <CardTitle>Upload Details</CardTitle>
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
                          Type: {file.file_type} • Rows: {file.row_count}
                        </p>
                      </div>
                    </div>
                    <Badge variant={file.detected ? "default" : "secondary"}>
                      {file.detected ? "Detected" : "Unknown"}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* GSTR Download */}
        {gstrData && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Generated GSTR Files</CardTitle>
              <CardDescription>Download your portal-ready JSON files</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                <Button
                  onClick={() => handleDownload("gstr1b")}
                  className="w-full"
                  variant="outline"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download GSTR-1B
                </Button>
                <Button
                  onClick={() => handleDownload("gstr3b")}
                  className="w-full"
                  variant="outline"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download GSTR-3B
                </Button>
              </div>

              {/* Preview Summary */}
              <div className="mt-6 grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h4 className="font-semibold mb-2">GSTR-1B Summary</h4>
                  <ul className="text-sm space-y-1">
                    <li>Table 7 (B2C Others): {gstrData.gstr1b?.table7?.length || 0} entries</li>
                    <li>Table 13 (Documents): {gstrData.gstr1b?.table13?.length || 0} entries</li>
                    <li>Table 14 (ECO): {gstrData.gstr1b?.table14?.length || 0} entries</li>
                  </ul>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h4 className="font-semibold mb-2">GSTR-3B Summary</h4>
                  <ul className="text-sm space-y-1">
                    <li>Taxable Value: ₹{gstrData.gstr3b?.section_31?.txval?.toFixed(2) || 0}</li>
                    <li>IGST: ₹{gstrData.gstr3b?.section_31?.iamt?.toFixed(2) || 0}</li>
                    <li>CGST: ₹{gstrData.gstr3b?.section_31?.camt?.toFixed(2) || 0}</li>
                    <li>SGST: ₹{gstrData.gstr3b?.section_31?.samt?.toFixed(2) || 0}</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Previous Uploads */}
        {uploads.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Previous Uploads</CardTitle>
              <CardDescription>View and download from previous uploads</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {uploads.slice(0, 10).map((upload) => (
                  <div
                    key={upload.id}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                    onClick={() => loadUploadDetails(upload.id)}
                  >
                    <div>
                      <p className="font-medium">
                        {new Date(upload.upload_date).toLocaleString()}
                      </p>
                      <p className="text-sm text-slate-600">
                        {upload.files?.length || 0} files • {upload.metadata?.gstin || "N/A"}
                      </p>
                    </div>
                    <Badge
                      variant={
                        upload.status === "completed"
                          ? "default"
                          : upload.status === "failed"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {upload.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default App;
