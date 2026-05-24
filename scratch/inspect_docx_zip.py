import zipfile

with zipfile.ZipFile("manual.docx", "r") as z:
    print("Files in manual.docx:")
    media_files = [f for f in z.namelist() if f.startswith("word/media/")]
    print(f"Total media files: {len(media_files)}")
    for f in sorted(media_files)[:20]:
        info = z.getinfo(f)
        print(f"  {f} - size={info.file_size} bytes, compressed={info.compress_size} bytes")
    if len(media_files) > 20:
        print("  ...")
