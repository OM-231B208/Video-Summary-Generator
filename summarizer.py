# from transformers import pipeline

# # Dictionary to cache summarization models
# # Key  -> model name (e.g. facebook/bart-large-cnn)
# # Value -> loaded Hugging Face pipeline
# # Isse model baar-baar load nahi hota (memory + time save hota hai)
# _summarizers = {}

# # Function to get summarizer model
# # Agar model pehle se load hai toh wahi use hoga
# # Nahi toh naya model load karke cache me store kar denge
# def get_summarizer(model_name: str):
#     if model_name not in _summarizers:
#         # Summarization pipeline load kar rahe hain
#         _summarizers[model_name] = pipeline(
#             "summarization",
#             model=model_name
#         )
#     return _summarizers[model_name]


# # Function to summarise text using a pre-trained Hugging Face model
# # Default model: facebook/bart-large-cnn
# # max_length / min_length token length hoti hai (tokens = words ya subwords)
# def summarize_text(
#     text: str,
#     model_name: str = "facebook/bart-large-cnn",
#     max_length: int = 180,
#     min_length: int = 80
# ) -> str:
#     # Cached summarizer model fetch kar rahe hain
#     summarizer = get_summarizer(model_name)

#     # Text ko summarize kar rahe hain
#     # do_sample=False ka matlab:same input pe hamesha same output milega (deterministic output)
#     result = summarizer(
#         text,
#         max_length=max_length,
#         min_length=min_length,
#         do_sample=False
#     )

#     # Hugging Face output ek list hoti hai
#     # Pehle element ke andar summary_text hota hai
#     return result[0]["summary_text"]
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    pipeline
)
import torch

# Cache: model_name → loaded pipeline
_summarizers = {}


def get_summarizer(model_name: str):
    """
    Returns a cached text2text-generation pipeline for the given model.
    Uses 'text2text-generation' task because 'summarization' was removed
    in transformers >= 4.52.
    """
    if model_name not in _summarizers:
        device    = "cuda" if torch.cuda.is_available() else "cpu"
        device_id = 0 if device == "cuda" else -1
        dtype     = torch.float16 if device == "cuda" else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model     = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=dtype
        )

        _summarizers[model_name] = pipeline(
            "text2text-generation",   # ← fixed task name
            model=model,
            tokenizer=tokenizer,
            device=device_id,
            framework="pt"
        )

    return _summarizers[model_name]


def summarize_text(
    text: str,
    model_name: str = "facebook/bart-large-cnn",
    max_length: int = 180,
    min_length: int = 80
) -> str:
    """
    Summarize text using a pre-trained Hugging Face seq2seq model.
    Returns the summary string.
    """
    summarizer = get_summarizer(model_name)

    result = summarizer(
        text,
        max_new_tokens=max_length,
        min_new_tokens=min_length,
        num_beams=4,
        do_sample=False,
        truncation=True
    )

    # text2text-generation returns "generated_text" key
    item = result[0]
    return item.get("generated_text") or item.get("summary_text") or ""
