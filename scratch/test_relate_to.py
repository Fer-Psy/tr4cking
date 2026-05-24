import docx

doc = docx.Document()
screenshot_path = "screenshots/01_login.png"

# Get or add image part
img_part = doc.part.get_or_add_image(screenshot_path)
print(f"img_part: {img_part}")

# Relate to
rId = doc.part.relate_to(img_part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
print(f"rId registered successfully: {rId}")
print("Relationships:")
for rId_key, rel in doc.part.rels.items():
    print(f"  {rId_key} -> {rel.target_ref}")
