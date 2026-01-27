from bs4 import BeautifulSoup

with open("latest_taaft.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

for s in soup(['style', 'script']):
    s.decompose()

sections = ["Breaking News", "Coming in Hot", "Today’s Spotlight", "AI Finds", "Notable AIs", "Open Source Finds", "Prompt of the Day"]

print("--- START ANALYSIS ---")

for text_to_find in sections:
    print(f"\nLooking for: {text_to_find}")
    # Search for any tag containing the text
    tag = soup.find(lambda t: t.name in ['b', 'strong', 'h1', 'h2', 'h3', 'span', 'p'] and text_to_find in t.get_text())
    if tag:
        print(f"FOUND {tag.name}: {tag.get_text().strip()}")
        # Traverse siblings
        current = tag
        count = 0
        while current and count < 30:
            current = current.find_next(['a', 'p', 'span', 'div'])
            if current:
                txt = current.get_text().strip()
                if txt:
                    is_link = current.name == 'a'
                    print(f"  [{current.name}] {'(LINK)' if is_link else ''} {txt[:100]}...")
                    if is_link:
                        print(f"    URL: {current.get('href')}")
            count += 1
    else:
        print(f"NOT FOUND: {text_to_find}")
