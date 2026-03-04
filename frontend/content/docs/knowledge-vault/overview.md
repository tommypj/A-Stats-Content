## What is the Knowledge Vault?

The Knowledge Vault is a private document library that makes AI-generated content smarter and more accurate for your specific business. Upload your internal documents — product specs, style guides, research reports, brand guidelines — and the AI will draw on that material when generating outlines and articles.

Without a Knowledge Vault, the AI works entirely from its general training data. With it, generated content reflects your proprietary knowledge, terminology, and positioning.

## How RAG Works

RAG stands for Retrieval-Augmented Generation. When you trigger AI generation, the platform runs a two-step process:

1. **Retrieval** — The system searches your uploaded documents for passages that are semantically relevant to the current topic or prompt. It does not do a simple keyword search; it matches meaning, so related concepts surface even when exact words differ.

2. **Augmentation** — The retrieved passages are injected into the AI prompt as additional context. The model then generates content that incorporates that context alongside its general knowledge.

The result is output that sounds like it comes from someone who has read your internal materials, not a generic AI assistant.

> **Tip:** The more specific and well-organized your source documents are, the more precisely the retrieval step can match relevant passages to each generation task.

## Supported File Types

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text-based PDFs only; scanned image PDFs are not supported |
| Word Document | `.docx` | Both modern and legacy Word formats accepted |
| Plain Text | `.txt` | UTF-8 encoding recommended |

Scanned PDFs that contain only images of text cannot be processed because there is no extractable text layer. Use an OCR tool to convert them before uploading.

## What the Knowledge Vault Improves

### Brand Accuracy
If your product has specific names, acronyms, or technical terms that the general AI model may not know or may confuse, uploading product documentation ensures those terms appear correctly in generated content.

### Factual Grounding
Research reports, data summaries, and case studies give the AI concrete facts and statistics to reference, reducing the likelihood of hallucinated figures.

### Consistent Tone and Messaging
Style guides and messaging frameworks uploaded to the vault help the AI maintain consistent language patterns, preferred phrasing, and positioning across all generated articles.

### Competitive Differentiation
Internal competitive analyses or positioning documents allow the AI to naturally weave in differentiation points without requiring you to include them in every prompt.

## Scope: Project-Level Knowledge

Knowledge Vault sources are scoped to the project they are uploaded to. Sources uploaded to Project A are not available when generating content in Project B. This lets you maintain separate knowledge bases for different clients, brands, or product lines.

> **Tip:** If you manage multiple projects that share a common knowledge base (for example, a company-wide style guide), upload the same document to each project that needs it.

## Getting Started

1. Navigate to a project and open the **Knowledge Vault** section from the sidebar.
2. Upload one or more documents using the upload button.
3. Wait for processing to complete (a status indicator shows progress).
4. Generate an article or outline as normal — the vault is used automatically.

No additional configuration is required. Once sources are processed, they are active for all subsequent generation tasks in that project.
