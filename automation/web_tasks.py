import webbrowser





ALIASES = {
    "chartgpt": "chatgpt",
    "chatgpt": "chatgpt",
    "chat gpt": "chatgpt",
    "open ai": "openai",
    "open-ai": "openai",
    "tiktok": "tiktok","yt": "youtube",
    "insta": "instagram",
    "fb": "facebook",
}


KNOWN_SITES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "chatgpt": "https://chat.openai.com",
    "openai": "https://openai.com",
    "tiktok": "https://www.tiktok.com",
}


def normalize(text):
    text = text.lower().strip()
    text = text.replace(" ", "")
    return ALIASES.get(text, text)


def open_website(site_name):
    raw_input = site_name

    site_name = normalize(site_name)

    print(f"[WEB DEBUG] Received: {raw_input}")
    print(f"[WEB DEBUG] Normalized: {site_name}")

    if site_name in KNOWN_SITES:
        url = KNOWN_SITES[site_name]
        webbrowser.open(url)
        return f"Opening {site_name}"


    url = f"https://www.google.com/search?q={site_name}"
    webbrowser.open(url)
    return f"Searching Google for {site_name}"