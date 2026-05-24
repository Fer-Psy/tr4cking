import docx

doc = docx.Document("manual.docx")
print("First 100 paragraphs that contain text:")
count = 0
for idx, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if text:
        print(f"P[{idx}] (style={p.style.name}): {text[:100]}")
        count += 1
        if count >= 100:
            break
