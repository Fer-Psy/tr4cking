import os
import hashlib

folder = "screenshots"
files = [f for f in os.listdir(folder) if f.endswith(".png")]

hashes = {}
for f in sorted(files):
    path = os.path.join(folder, f)
    with open(path, "rb") as fh:
        data = fh.read()
        h = hashlib.sha256(data).hexdigest()
        hashes[h] = hashes.get(h, []) + [f]

print(f"Total files: {len(files)}")
print(f"Unique hashes: {len(hashes)}")
for h, fs in hashes.items():
    print(f"Hash {h[:12]}... contains {len(fs)} files:")
    print(f"  {fs[:5]}")
    if len(fs) > 5:
        print("  ...")
