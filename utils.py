import re

# -------------------------------
# Sentence-aware text chunking
# -------------------------------
def chunk_text(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200
) -> list:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]

        # avoid cutting in middle of sentence
        sentence_end = re.search(r'[.!?](?!.*[.!?])', chunk)
        if sentence_end:
            end = start + sentence_end.end()
            chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap

        if start < 0:
            start = 0

    return chunks


# -------------------------------
# Hierarchical (two-stage) summarization
# -------------------------------
def chunked_summarize(
    text: str,
    summarize_func,
    max_chunk_size: int = 2000
) -> str:
    """
    summarize_func:
        A GPU/CPU-enabled summarization function.
        utils.py does NOT control device — it only calls it.
    """

    # STEP 1: Split long text into sentence-safe chunks
    text_chunks = chunk_text(
        text,
        chunk_size=max_chunk_size,
        overlap=200
    )

    # STEP 2: Summarize each chunk
    # (GPU will be used automatically if summarize_func is GPU-enabled)
    partial_summaries = [
        summarize_func(
            chunk,
            max_length=220,
            min_length=100
        )
        for chunk in text_chunks
    ]

    # STEP 3: Combine partial summaries
    combined_summary_input = " ".join(partial_summaries)

    # STEP 4: Final summarization for coherence
    final_summary = summarize_func(
        combined_summary_input,
        max_length=200,
        min_length=120
    )

    return final_summary


# -------------------------------
# Wrapper used by main.py
# -------------------------------
def enhanced_summarize(
    text: str,
    summarize_func
) -> str:
    """
    Wrapper function to keep main.py clean.
    GPU/CPU decision is handled INSIDE summarize_func.
    """
    return chunked_summarize(
        text=text,
        summarize_func=summarize_func,
        max_chunk_size=2000
    )


# -------------------------------
# Summary formatting
# -------------------------------
def format_summary(
    summary: str,
    summary_format: str
) -> str:
    if summary_format == "bullet":
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        return "\n".join(
            f"- {s.strip()}" for s in sentences if s.strip()
        )
    return summary
