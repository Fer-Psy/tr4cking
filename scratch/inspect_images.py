import docx

doc = docx.Document("manual.docx")
shapes = list(doc.inline_shapes)
print(f"Total inline shapes: {len(shapes)}")

for idx, shape in enumerate(shapes):
    try:
        img = shape.image
        print(f"Shape {idx}: filename={img.filename}, sha1={img.sha1[:8] if img.sha1 else 'None'}, size={img.blob.__sizeof__()} bytes, type={shape.type}")
    except Exception as e:
        print(f"Shape {idx}: error {e}")
    if idx >= 15:
        print("...")
        break
