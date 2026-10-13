import bleach

def sanitize_text(text: str) -> str:
    return bleach.clean(text, tags=[], attributes={}, strip=True).strip()
