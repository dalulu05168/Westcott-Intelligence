from pathlib import Path
import zipfile,sys
root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root.with_suffix('.zip')
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts:
   z.write(p,arcname=p.relative_to(root))
print(out)
