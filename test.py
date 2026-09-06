import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import json

def parser(epub_path, output_json="text.json"):
    book = epub.read_epub(epub_path)
    lines = []

    for item in book.get_items():
        if item.get_type() == 9: #document
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    lines.append(line)
    
    f = open(output_json, "w", encoding="utf-8")
    json.dump(lines, f, ensure_ascii=False, indent=2)
    f.close()

    return lines

if __name__ == "__main__":
    lines = parser("book.epub")
    print(f"extracted {len(lines)} lines")