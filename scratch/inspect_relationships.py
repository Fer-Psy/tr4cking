import docx

doc = docx.Document("manual.docx")
shapes = list(doc.inline_shapes)

print("Document Relationships:")
for rId, rel in doc.part.rels.items():
    if "image" in rel.reltype:
        print(f"  rId: {rId} -> target: {rel.target_ref}, type: {rel.reltype}")

print("\nInline Shapes mapping to Relationship IDs:")
for idx, shape in enumerate(shapes):
    inline = shape._inline
    # Search for any blip elements using xpath
    blips = inline.xpath('.//a:blip')
    rId = None
    if blips:
        rId = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
    
    # Also find wp:docPr
    docPrs = inline.xpath('.//wp:docPr')
    name = docPrs[0].get('name') if docPrs else "None"
    descr = docPrs[0].get('descr') if docPrs else "None"
    
    print(f"Shape {idx}: name='{name}', desc='{descr}', rId='{rId}'")
