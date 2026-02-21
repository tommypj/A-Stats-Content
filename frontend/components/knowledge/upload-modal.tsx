"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, X, CheckCircle, AlertCircle } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { api, parseApiError } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const ALLOWED_TYPES = ["application/pdf", "text/plain", "text/markdown", "text/html", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".html", ".docx"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  const resetForm = () => {
    setFile(null);
    setTitle("");
    setDescription("");
    setTags("");
    setError("");
    setUploadProgress(0);
  };

  const handleClose = () => {
    if (!isUploading) {
      resetForm();
      onClose();
    }
  };

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return "File size exceeds 10MB limit";
    }

    // Check file type
    const extension = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension) && !ALLOWED_TYPES.includes(file.type)) {
      return "Invalid file type. Only PDF, TXT, MD, HTML, and DOCX files are allowed";
    }

    return null;
  };

  const handleFileSelect = (selectedFile: File) => {
    setError("");
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setFile(selectedFile);
    // Auto-populate title from filename if not set
    if (!title) {
      const filename = selectedFile.name.replace(/\.[^/.]+$/, "");
      setTitle(filename);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setIsUploading(true);
      setUploadProgress(0);

      // Simulate upload progress (since FormData doesn't provide real progress)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      await api.knowledge.upload(file, title, description, tags);

      clearInterval(progressInterval);
      setUploadProgress(100);

      toast.success("File uploaded successfully!");
      setTimeout(() => {
        handleClose();
        onSuccess?.();
      }, 500);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to upload file");
      setError(apiError.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Knowledge Source"
      description="Upload documents to expand your knowledge base"
      size="lg"
    >
      <div className="space-y-4">
        {/* Drag & Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={cn(
            "border-2 border-dashed rounded-xl p-8 text-center transition-all",
            isDragging
              ? "border-primary-500 bg-primary-50"
              : file
              ? "border-green-500 bg-green-50"
              : error
              ? "border-red-500 bg-red-50"
              : "border-surface-tertiary hover:border-primary-500 hover:bg-surface-secondary"
          )}
        >
          {file ? (
            <div className="space-y-2">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
              <div className="flex items-center justify-center gap-2">
                <FileText className="h-5 w-5 text-text-muted" />
                <p className="font-medium text-text-primary">{file.name}</p>
                <button
                  onClick={() => setFile(null)}
                  className="p-1 hover:bg-surface-tertiary rounded"
                >
                  <X className="h-4 w-4 text-text-muted" />
                </button>
              </div>
              <p className="text-sm text-text-muted">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {error ? (
                <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
              ) : (
                <Upload className="h-12 w-12 text-text-muted mx-auto" />
              )}
              <div>
                <p className="font-medium text-text-primary">
                  {error || "Drag & drop your file here"}
                </p>
                <p className="text-sm text-text-muted mt-1">or</p>
                <label className="inline-block">
                  <input
                    type="file"
                    className="hidden"
                    accept={ALLOWED_EXTENSIONS.join(",")}
                    onChange={handleFileInputChange}
                    disabled={isUploading}
                  />
                  <span className="text-sm text-primary-500 hover:text-primary-600 cursor-pointer font-medium">
                    Browse files
                  </span>
                </label>
              </div>
              <p className="text-xs text-text-muted">
                Supports: PDF, TXT, MD, HTML, DOCX (max 10MB)
              </p>
            </div>
          )}
        </div>

        {/* Form Fields */}
        {file && (
          <div className="space-y-4">
            <Input
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a descriptive title"
              helperText="Optional - defaults to filename"
            />

            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add a description to help with search and organization"
              rows={3}
              helperText="Optional - describe what this document contains"
            />

            <Input
              label="Tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="research, analysis, documentation"
              helperText="Optional - comma-separated tags for organization"
            />
          </div>
        )}

        {/* Upload Progress */}
        {isUploading && (
          <div className="space-y-2">
            <div className="w-full bg-surface-tertiary rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-sm text-text-muted text-center">
              Uploading... {uploadProgress}%
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={handleClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || isUploading}
            isLoading={isUploading}
          >
            Upload
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
