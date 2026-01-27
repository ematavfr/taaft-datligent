from bs4 import BeautifulSoup

with open("latest_taaft.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Clean up the soup to see headers clearly
for s in soup(['style', 'script']):
    s.decompose()

print("--- ALL TEXT HEADERS ---")
for tag in soup.find_all(['h1', 'h2', 'h3', 'b', 'strong']):
    text = tag.get_text().strip()
    if text:
        print(f"[{tag.name}] {text}")

print("\n--- ALL LINKS ---")
for a in soup.find_all('a', href=True):
    text = a.get_text().strip()
    if text:
        print(f"{text}: {a['href']}")
