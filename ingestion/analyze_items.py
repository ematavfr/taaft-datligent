from bs4 import BeautifulSoup

with open("latest_taaft.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

for s in soup(['style', 'script']):
    s.decompose()

# A very simple recursive extraction
def print_simple(elem, depth=0):
    if hasattr(elem, 'name') and elem.name:
        text = elem.get_text(strip=True)
        if text:
            # If it has a link, print it
            a = elem.find('a', href=True)
            link = f" ({a['href']})" if a else ""
            print("  " * depth + f"<{elem.name}>: {text}{link}")
        for child in elem.children:
            print_simple(child, depth + 1)

# Let's just print the text content of divs that contain <b> tags (potential headers)
for b in soup.find_all('b'):
    text = b.get_text(strip=True)
    if text in ["Breaking News", "Coming in Hot", "AI Finds", "Notable AIs", "Open Source Finds", "Prompt of the Day"]:
        print(f"\n--- SECTION: {text} ---")
        # Look at the parent or siblings to find items
        parent = b.find_parent('td')
        if parent:
            # Print next few paragraphs or spans
            next_elems = parent.find_all_next(['p', 'span', 'a'], limit=20)
            for e in next_elems:
                if e.name == 'a' and e.get_text(strip=True):
                    print(f"ITEM: {e.get_text(strip=True)} -> {e['href']}")
                elif e.name in ['p', 'span']:
                    t = e.get_text(strip=True)
                    if t and len(t) > 10: # Likely description
                        print(f"DESC: {t[:100]}...")

if __name__ == "__main__":
    # The logic is already outside the main block in the previous version, 
    # but I'll move it inside for clarity or just let it run.
    # Wait, the previous version had logic outside main. Let me check why it didn't output.
    pass
