#!/usr/bin/env python3
"""Local ParshaPulse file tools. Python 3.9+, standard library only."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '__pycache__', 'private', '.DS_Store'}


def project_files(root=ROOT):
    return sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink()
                  and not any(part in EXCLUDED for part in p.relative_to(root).parts)
                  and p.suffix not in {'.zip', '.pyc'})


def check():
    errors = []
    for name in ['README.md', 'VERSION', 'project.json', 'TODO.md', 'CHANGELOG.md',
                 'docs/ORIGINAL-RESPONSE.md', 'docs/FOUNDATION.md', 'START-HERE.html']:
        if not (ROOT / name).is_file():
            errors.append('Missing: ' + name)
    try:
        project = json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
        version = (ROOT/'VERSION').read_text(encoding='utf-8').strip()
        if project['version'] != version:
            errors.append('VERSION and project.json differ')
        algos = json.loads((ROOT/'data/algorithms.json').read_text(encoding='utf-8'))
        tasks = json.loads((ROOT/'data/tasks.json').read_text(encoding='utf-8'))
        if len(algos) != 28 or len({x['id'] for x in algos}) != 28:
            errors.append('Expected 28 unique algorithms')
        if len(tasks) != 120 or len({x['id'] for x in tasks}) != 120:
            errors.append('Expected 120 unique tasks')
        for row in algos:
            if not (ROOT/row['path']).is_file():
                errors.append('Missing algorithm: '+row['path'])
        todo=(ROOT/'TODO.md').read_text(encoding='utf-8')
        for t in tasks:
            mark='x' if t['done'] else ' '
            if f'- [{mark}] **{t["id"]}** — {t["title"]}' not in todo:
                errors.append('Task mismatch: '+t['id'])
    except (OSError, ValueError, KeyError) as e:
        errors.append('Metadata: '+str(e))
    count=0
    for p in project_files():
        if p.suffix != '.md':
            continue
        text=p.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^\s]+?)\)',text):
            if target.startswith(('https:', 'http:', 'mailto:', 'tel:', '#')) or '{{' in target:
                continue
            target=target.split('#',1)[0]
            if not target:
                continue
            count+=1
            resolved=(p.parent/target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f'Broken link {p.relative_to(ROOT)} -> {target}')
    result={'ok':not errors,'relative_links_checked':count,'files':len(project_files()),'errors':errors}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not errors else 1


def new_week(args):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',args.slug):
        raise ValueError('Use a slug of 1–80 ASCII letters, digits, underscores or hyphens')
    date=dt.date.fromisoformat(args.date)
    dest=ROOT/'weeks'/args.slug
    # Refuse overwrite. Date is recorded, never used to infer the parsha.
    dest.mkdir(parents=True,exist_ok=False)
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    header=f'# 📖 {args.name}\n\nתיק טיוטה · נוצר: {stamp}\n\n'
    text=header+f'''טווח: {args.reference}
תאריך אזרחי יעד: {date.isoformat()}
תאריך עברי, מקום ומנהג: להשלמה
אימות לוח: pending — נדרש מקור חיצוני שנבדק בידי הלומד

## התחלה

- [תבנית שבוע](../../templates/WEEK.md)
- [מפתח מתכונים](../../algorithms/INDEX.md)
- [סיכום מפגש](SESSION.md)
- [מקטע ראשון](SEGMENT.md)

## שאלת השבוע

להשלמה.

## מקורות ושאלות פתוחות

להשלמה. אין להציג את התאריך כאימות התאמת הפרשה.

## קרדיטים

Cyber Shamanic / AnLoMinus · [קרדיטים ומקורות](../../CREDITS.md).

> כְּשֶׁאָדָם אוֹמֵר חִדּוּשֵׁי אוֹרַיְתָא, עַל יְדֵי זֶה מְשַׂמֵּחַ אֶת הַשֵּׁם יִתְבָּרַךְ.
> — רבי נחמן מברסלב, ספר המידות, לימוד א׳, ג׳.
'''
    (dest/'README.md').write_text(text,encoding='utf-8')
    for name in ['SESSION','SEGMENT']:
        content=(ROOT/'templates'/f'{name}.md').read_text(encoding='utf-8')
        # Template footer is relative to templates/; new week is one level deeper.
        content=content.replace('(../CREDITS.md)','(../../CREDITS.md)')
        (dest/f'{name}.md').write_text(content,encoding='utf-8')
    (dest/'week.json').write_text(json.dumps({'name':args.name,'reference':args.reference,
        'target_date':date.isoformat(),'calendar_status':'pending','created_at':stamp,
        'hebrew_date':None,'location_custom':None},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(str(dest))
    return 0


def package(args):
    output=Path(args.output).expanduser().resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('Output filename must end in .zip')
    if output.exists():
        raise FileExistsError('Refusing to overwrite '+str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    files=project_files()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p,'ParshaPulse/'+p.relative_to(ROOT).as_posix())
    print(json.dumps({'archive':str(output),'files':len(files),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check',help='Check metadata, files, tasks and relative Markdown links')
    week=sub.add_parser('new-week',help='Create a new week draft; no calendar inference')
    for field in ['slug','name','reference','date']:
        week.add_argument('--'+field,required=True)
    pack=sub.add_parser('package',help='Create ZIP; exclude private, .git and ZIP files')
    pack.add_argument('--output',required=True)
    args=parser.parse_args()
    try:
        if args.command=='check': return check()
        if args.command=='new-week': return new_week(args)
        return package(args)
    except (OSError,ValueError) as e:
        print('Error: '+str(e),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
