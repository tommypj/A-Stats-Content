## What is Knowledge Querying?

Beyond powering AI article generation automatically, the Knowledge Vault has a direct query interface. You can type a question or topic and get a synthesized answer drawn from your uploaded documents. This is useful for quickly checking what your internal documents say about a topic, or for verifying that a key piece of information is captured in the vault before relying on it in generation.

## How to Query

1. Navigate to your project's **Knowledge Vault** page.
2. Click the **Query Knowledge** tab or button (depending on your project layout).
3. Type your question in the input field.
4. Click **Search** or press **Enter**.

The system retrieves the most relevant passages from your indexed sources and generates a synthesized response. The response also lists which source documents were used, so you can verify the provenance of the answer.

## Example Questions

Effective queries are specific and phrased as questions or clear topics:

**Product information**
- "What are the key differentiators of our Pro plan versus competitors?"
- "What integrations does the platform support?"
- "What is the recommended onboarding sequence for new enterprise clients?"

**Brand and tone**
- "What tone of voice should be used in blog posts?"
- "What phrases are discouraged in our brand style guide?"
- "How do we describe our approach to data privacy?"

**Research and statistics**
- "What conversion rate benchmarks are mentioned in the Q3 report?"
- "What does the competitive analysis say about pricing strategy?"

> **Tip:** If a query returns a weak or irrelevant answer, try rephrasing it more specifically. "Tell me about pricing" is less effective than "What are the prices for each subscription plan?"

## How Responses Are Generated

When you submit a query, the system performs these steps:

1. **Semantic search** — Your query is converted into a vector embedding and compared against all stored document chunks. The top matching chunks are retrieved based on semantic similarity, not just keyword overlap.

2. **Context assembly** — The retrieved chunks (up to a configured limit) are assembled into a context window alongside your original query.

3. **Answer synthesis** — The AI model reads the assembled context and generates a coherent, natural-language response. It uses only the retrieved content to answer; it does not supplement with general knowledge in the same way as article generation.

4. **Source attribution** — The response includes references to the source documents that contributed to the answer.

## Accuracy and Limitations

### What Works Well
- Factual questions with clear answers present in the uploaded documents
- Terminology and definition lookups
- Summarizing a specific section of a document
- Checking consistency of messaging across documents

### Known Limitations
- The system can only answer questions based on content that has been uploaded. If information is not in any source document, it cannot be retrieved.
- Long documents are split into chunks, and very long answers may require information from multiple chunks that do not all get retrieved in a single query.
- Heavily formatted documents (tables, bullet-heavy slides exported to PDF) may not parse as cleanly as prose-based documents, which can affect retrieval quality.

> **Tip:** If you notice the AI consistently missing a key fact during article generation, try querying for that fact directly. If it does not surface, the relevant document may need to be re-uploaded or the information added to a document that is already in the vault.

## Using Query Results to Improve Generation

The query interface is a diagnostic tool as much as a reference tool. Use it to:

- **Verify coverage** — Confirm that critical information is indexed before running a large batch of article generation.
- **Debug weak output** — If generated articles lack specific detail, query for that detail to see whether the vault has the relevant content.
- **Spot gaps** — If a query returns a poor result, you know which document you need to upload to fill that gap.

## Result Limits and Performance

Each query retrieves up to 500 document chunks for context assembly. For typical business documents, this is more than sufficient. Very large knowledge vaults (dozens of large documents) may see slightly slower response times on complex queries, but accuracy is not affected by vault size — only retrieval speed.
