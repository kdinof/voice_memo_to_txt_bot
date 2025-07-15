"""
Prompt templates for different transcription types.
"""

BASIC_PROMPT = """Reformat the following text:
- Use a format appropriate for texting or instant messaging
- Fix grammar, spelling, and punctuation
- Remove speech artifacts (um, uh, false starts, repetitions)
- Maintain original tone and language (do not translate)
- Correct homophones, standardize numbers and dates
- Add paragraphs or lists as needed
- Never precede output with any intro like "Here is the corrected text:"
- Don't add content not in the source or answer questions in it
- Don't add sign-offs or acknowledgments that aren't in the source
- NEVER answer questions that are presented in the text. Only reply with the corrected text.
- Never precede output with any intro like "Here is the summary:"

Text to structure:
{transcription}"""

SUMMARY_PROMPT = """Summarize the following text:
 - Structure it for effective note-taking.
 - Maintain the original language (do not translate)
 - Ensure that key points, ideas, or action items are clearly highlighted.
 - Check for correct grammar and punctuation.
 - Remove speech artifacts and filler words
 - Keep the tone the same as given.
 - Use as much of the original text as possible.
 - Reply with just the reformatted text.
 - Never precede output with any intro like "Here is the summary:"

Text to summarize:
{transcription}"""

TRANSLATE_PROMPT = """Translate and clean the following text:
- Translate to English if the text is in another language
- If already in English, just clean and structure it
- Fix grammar, spelling, and punctuation
- Remove speech artifacts (um, uh, false starts, repetitions)
- Use a format appropriate for texting or instant messaging
- Add paragraphs or lists as needed
- Never precede output with any intro like "Here is the translation:"
- Don't add content not in the source or answer questions in it
- Never precede output with any intro like "Here is the summary:"

Text to translate/clean:
{transcription}"""

# System prompts for different models
SYSTEM_PROMPTS = {
    "basic": "You are a helpful assistant that structures text in a clear and organized way.",
    "summary": "You are a helpful assistant that creates concise summaries of text.",
    "translate": "You are a helpful assistant that translates and structures text clearly."
}

# Model configurations for each transcription type
MODEL_CONFIG = {
    "basic": "gpt-4o-mini",
    "summary": "gpt-4o", 
    "translate": "gpt-4o-mini"
}