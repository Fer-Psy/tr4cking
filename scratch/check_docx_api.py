import docx
doc = docx.Document()
part = doc.part
print("Methods in doc.part:")
for m in sorted(dir(part)):
    if any(k in m.lower() for k in ["image", "rel", "add"]):
        print(f"  {m}")
