## Supported File Types

The Knowledge Vault accepts three file formats:

- **PDF** (`.pdf`) — Text-based documents. Scanned image PDFs are not supported; the file must contain a real text layer.
- **Word** (`.docx`) — Microsoft Word documents. Both `.docx` and older `.doc` formats are accepted where indicated.
- **Plain text** (`.txt`) — Simple text files. UTF-8 encoding is recommended to ensure special characters are preserved.

> **Tip:** If you have a scanned PDF, run it through an OCR tool such as Adobe Acrobat or a free online service to convert it to a text-layer PDF before uploading.

## Size Limits

Individual files are limited to **10 MB** per upload. This covers most business documents comfortably — a typical 50-page Word report is well under this threshold.

If you have very large documents, consider splitting them into logical sections (for example, one file per chapter or topic area). Smaller, focused documents also produce better retrieval results because the content is more tightly scoped.

## How to Upload

1. Open the project where you want to add knowledge sources.
2. Click **Knowledge Vault** in the left sidebar.
3. Click the **Upload Source** button in the top-right corner.
4. Select one or more files from your computer using the file picker, or drag and drop files onto the upload area.
5. Optionally enter a name and description for each source so you can identify it later.
6. Click **Upload** to begin processing.

You can upload multiple files in a single session. Each file is queued and processed independently.

## Processing Time

After uploading, each document goes through a processing pipeline:

1. Text is extracted from the file.
2. The text is split into chunks of manageable size.
3. Each chunk is converted into a vector embedding and stored in the knowledge index.

Processing typically completes in **10–60 seconds** for most documents. Larger files may take a few minutes. A status indicator on the source card shows the current state:

| Status | Meaning |
|--------|---------|
| Processing | The document is being indexed |
| Ready | The source is active and will be used in generation |
| Failed | Processing encountered an error — see the error message |

Do not navigate away during initial upload, but you can safely leave the Knowledge Vault page once the upload has been submitted. Processing continues in the background.

## Managing Sources

### Viewing Sources
All uploaded sources appear in a list on the Knowledge Vault page. Each card shows the file name, description, processing status, upload date, and an approximate chunk count (the number of text segments stored in the index).

### Editing Source Details
Click the edit icon on any source card to update its display name or description. Changing these fields does not re-process the document.

### Deleting Sources
Click the delete icon on a source card and confirm the deletion. The document and all its associated vector embeddings are removed immediately. Any future generation tasks in the project will no longer have access to that source's content.

> **Tip:** Deleting a source does not affect articles that were already generated using it — those articles retain their content. Only future generation tasks are affected.

### Re-uploading Updated Documents
If a source document has been updated (for example, a product spec has a new version), delete the old source and upload the new file. There is no in-place update mechanism; the previous version must be removed first.

## Best Practices for Source Documents

- **Remove boilerplate** before uploading. Headers, footers, legal disclaimers, and navigation text that appear on every page add noise to the index without providing useful knowledge.
- **Use descriptive file names**. The file name is displayed in the source list and is used as context when naming sources. A name like `2024-brand-voice-guide.pdf` is more useful than `document1.pdf`.
- **One topic per file where possible**. Uploading a 200-page internal wiki as a single file is less effective than uploading individual sections focused on specific topics.
- **Check encoding for text files**. If your `.txt` file was exported from a legacy system, open it in a text editor and verify that special characters display correctly before uploading.
