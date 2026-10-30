from pathlib import Path
import re, html, json, posixpath

ROOT=Path(__file__).resolve().parents[1]
paths=sorted(p for p in ROOT.rglob('*.md') if '.github' not in p.parts and p.name!='ORIGINAL-RESPONSE.md')
paths.sort(key=lambda p: (p.name!='README.md' or p.parent!=ROOT,p.relative_to(ROOT).as_posix()))
ids={p.relative_to(ROOT).as_posix():f'doc-{i}' for i,p in enumerate(paths)}

def inline(s,current):
    s=html.escape(s,quote=False)
    def link(m):
        label,url=m.groups()
        raw=html.unescape(url)
        if raw.startswith(('http:','https:','mailto:')):
            return f'<a href="{html.escape(raw,quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
        if '{{' in raw: return label+' <code>'+html.escape(raw)+'</code>'
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(current),raw.split('#')[0]))
        target='#'+ids[resolved] if resolved in ids else raw
        if ':' in target and not target.startswith('#'): return label
        return f'<a href="{html.escape(target,quote=True)}">{label}</a>'
    s=re.sub(r'\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)',link,s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',s)
    return s

def render(text,current):
    lines=text.splitlines(); out=[]; i=0; listtype=None
    def close_list():
        nonlocal listtype
        if listtype: out.append('</'+listtype+'>'); listtype=None
    while i<len(lines):
        line=lines[i]; stripped=line.strip()
        if stripped.startswith('```'):
            close_list(); code=[]; i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i]); i+=1
            out.append('<pre dir="ltr"><code>'+html.escape('\n'.join(code))+'</code></pre>'); i+=1; continue
        if stripped.startswith('|') and i+1<len(lines) and re.match(r'^\s*\|[\s:|\-]+\|\s*$',lines[i+1]):
            close_list(); cells=lambda t:[c.strip() for c in t.strip().strip('|').split('|')]
            out.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+inline(c,current)+'</th>' for c in cells(line))+'</tr></thead><tbody>'); i+=2
            while i<len(lines) and lines[i].strip().startswith('|'):
                out.append('<tr>'+''.join('<td>'+inline(c,current)+'</td>' for c in cells(lines[i]))+'</tr>'); i+=1
            out.append('</tbody></table></div>'); continue
        if not stripped: close_list(); i+=1; continue
        if stripped=='---': close_list(); out.append('<hr>'); i+=1; continue
        heading=re.match(r'^(#{1,6})\s+(.+)',line)
        if heading:
            close_list(); lev=len(heading[1]); out.append(f'<h{lev}>'+inline(heading[2],current)+f'</h{lev}>'); i+=1; continue
        bullet=re.match(r'^\s*(?:([-*])\s+|(\d+)\.\s+)(.+)',line)
        if bullet:
            typ='ol' if bullet[2] else 'ul'
            if listtype!=typ: close_list(); out.append('<'+typ+'>'); listtype=typ
            content=bullet[3]
            mark=re.match(r'^\[([x ])\]\s*(.*)',content)
            if mark: content=('☑ ' if mark[1]=='x' else '☐ ')+mark[2]
            out.append('<li>'+inline(content,current)+'</li>'); i+=1; continue
        close_list()
        if stripped.startswith('>'):
            out.append('<blockquote>'+inline(stripped.lstrip('> '),current)+'</blockquote>'); i+=1; continue
        out.append('<p>'+inline(line,current)+'</p>'); i+=1
    close_list(); return '\n'.join(out)

nav=[]; articles=[]
for p in paths:
    rel=p.relative_to(ROOT).as_posix(); text=p.read_text(encoding='utf-8')
    heading=next((x.lstrip('# ').strip('* ') for x in text.splitlines() if x.strip()),p.stem)
    ident=ids[rel]
    nav.append(f'<a class="nav-link" href="#{ident}" data-doc="{ident}">{html.escape(heading)}<small dir="ltr">{html.escape(rel)}</small></a>')
    articles.append(f'<article id="{ident}" tabindex="-1"><div class="doc-meta">{html.escape(rel)}</div>{render(text,rel)}</article>')

tasks=json.loads((ROOT/'data/tasks.json').read_text(encoding='utf-8'))
taskhtml=[]
for group in dict.fromkeys(t['category'] for t in tasks):
    taskhtml.append('<fieldset><legend>'+html.escape(group)+'</legend>')
    for t in tasks:
        if t['category']==group:
            check=' checked' if t['done'] else ''
            taskhtml.append(f'<label class="task"><input type="checkbox" data-task="{t["id"]}"{check}><span><b>{t["id"]}</b> {html.escape(t["title"])}</span></label>')
    taskhtml.append('</fieldset>')

css='''
:root{color-scheme:light;--ink:#192e43;--muted:#4e6170;--paper:#fffdf8;--line:#d9dfe4;--gold:#b9862d;--nav:#102b40}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f0f3f5;color:var(--ink);font:18px/1.85 Arial,"Noto Sans Hebrew",sans-serif}button,input{font:inherit}button{cursor:pointer}a{color:#13568a;text-underline-offset:.2em}a:focus-visible,button:focus-visible,input:focus-visible,article:focus-visible{outline:3px solid #da8a12;outline-offset:3px}header{background:var(--nav);color:white;padding:1.3rem 2rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;border-bottom:4px solid var(--gold)}header h1{font-size:1.55rem;margin:0}header p{margin:0;color:#dde5ed;font-size:.9rem}.badge{border:1px solid #dcb467;background:#173c55;color:#fff1cf;border-radius:99px;padding:.15rem .9rem}.actions{display:flex;gap:.6rem;flex-wrap:wrap}.actions button,.tool{border:1px solid #b7c7d2;border-radius:.55rem;padding:.3rem .8rem;background:#fff;color:var(--ink)}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);max-width:1600px;margin:auto;min-height:80vh}aside{padding:1.2rem;background:#fff;border-inline-end:1px solid var(--line);max-height:calc(100vh - 130px);position:sticky;top:0;overflow:auto}aside input{width:100%;border:1px solid #8598a7;border-radius:.6rem;padding:.5rem;background:white;color:var(--ink)}.nav-link{display:block;padding:.6rem .7rem;border-bottom:1px solid #e4e8eb;text-decoration:none;color:var(--ink);font-size:.9rem}.nav-link small{display:block;font-size:.65rem;color:var(--muted);overflow-wrap:anywhere}.nav-link[aria-current=page]{border-inline-start:4px solid var(--gold);background:#edf4f8;font-weight:bold}main{padding:2rem;min-width:0}article{max-width:1000px;padding:2rem 2.5rem;background:var(--paper);border:1px solid var(--line);border-radius:1rem;box-shadow:0 8px 22px #132f4410;margin:0 auto 2rem}article h1{font-size:1.8rem;line-height:1.5;border-bottom:2px solid #e6d9bc;padding-bottom:1rem}article h2{font-size:1.3rem;margin-top:2rem}article h3{font-size:1.1rem}p{margin:.7rem 0}code{background:#eaf0f3;border-radius:.25rem;padding:.1rem .3rem;font-size:.85em;overflow-wrap:anywhere}pre{overflow:auto;background:#122d42;color:#f6f7fa;border-radius:.65rem;padding:1rem;text-align:left}pre code{background:transparent;color:inherit;white-space:pre;overflow-wrap:normal}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:.5rem}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:.65rem;text-align:right;border-bottom:1px solid var(--line);vertical-align:top}th{background:#e9f0f4}blockquote{margin:1rem 0;border-inline-start:4px solid var(--gold);padding:.6rem 1rem;background:#f7f0df}hr{border:0;border-top:1px solid var(--line);margin:2rem 0}.doc-meta{font:12px monospace;color:var(--muted);direction:ltr;text-align:left;overflow-wrap:anywhere}dialog{border:1px solid #b6c5cf;border-radius:1rem;max-width:900px;width:92vw;max-height:86vh;padding:1.6rem;color:var(--ink);background:var(--paper)}dialog::backdrop{background:#0b2133b8}dialog .close{float:left;border:0;background:#e9eef1;border-radius:.4rem;padding:.3rem .7rem}dialog h1{font-size:1.4rem}fieldset{border:1px solid var(--line);border-radius:.7rem;margin:1rem 0;padding:1rem}legend{font-weight:bold}.task{display:flex;gap:.7rem;align-items:flex-start;border-bottom:1px solid #e5e9ec;padding:.5rem}.task input{width:1.2rem;height:1.2rem;margin-top:.5rem;flex-shrink:0}.task b{font:12px monospace;display:block;color:var(--muted)}.task:has(input:checked) span{color:#496b51}footer{max-width:1000px;margin:1rem auto;padding:1rem;color:var(--muted);font-size:.8rem}.note{background:#e8eff5;padding:.7rem;border-radius:.5rem}.skip{position:absolute;top:-100px;right:1rem;background:white;padding:1rem;z-index:10}.skip:focus{top:1rem}[hidden]{display:none!important}@media(max-width:850px){header{align-items:flex-start;padding:1rem;flex-direction:column}.layout{display:block}aside{position:static;max-height:32vh;border-bottom:1px solid var(--line)}main{padding:1rem}article{padding:1.2rem;font-size:17px}article h1{font-size:1.4rem}}@media print{header,aside,.actions,footer,.doc-meta{display:none}body,main{background:white;padding:0}article{box-shadow:none;border:0;max-width:none;padding:0}a{color:inherit}pre{white-space:pre-wrap}tr{break-inside:avoid}}
'''
script='''
const docs=[...document.querySelectorAll('main > article')];
const links=[...document.querySelectorAll('.nav-link')];
const search=document.querySelector('#search');
const normalize=t=>t.normalize('NFD').replace(/[\\u0591-\\u05C7]/g,'').toLocaleLowerCase();
function show(id){const selected=document.getElementById(id);if(!selected||!docs.includes(selected))return;docs.forEach(d=>d.hidden=d!==selected);links.forEach(l=>{if(l.dataset.doc===id)l.setAttribute('aria-current','page');else l.removeAttribute('aria-current');});document.title=selected.querySelector('h1')?.textContent+' | ParshaPulse';selected.focus({preventScroll:true});window.scrollTo(0,0);}
function hash(){show(location.hash.slice(1)||'doc-0');}
window.addEventListener('hashchange',hash);hash();
search.addEventListener('input',()=>{const q=normalize(search.value.trim());let n=0;links.forEach(l=>{const d=document.getElementById(l.dataset.doc);const match=!q||normalize(d.textContent).includes(q);l.hidden=!match;if(match)n++;});document.querySelector('#results').textContent=n+' מסמכים';});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();search.focus();}});
document.querySelector('#version').addEventListener('click',()=>document.querySelector('#versions').showModal());
document.querySelector('#about-button').addEventListener('click',()=>document.querySelector('#about').showModal());
document.querySelector('#task-button').addEventListener('click',()=>{location.hash='tasks-view';show('tasks-view');});
document.querySelectorAll('dialog .close').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
document.querySelector('#print').addEventListener('click',()=>window.print());
let saved={};const storageKey='ParshaPulse.tasks.v0.0.2';
try{const parsed=JSON.parse(localStorage.getItem(storageKey)||'{}');if(parsed&&typeof parsed==='object'&&!Array.isArray(parsed))saved=parsed;}catch(e){document.querySelector('#storage-note').textContent='השמירה המקומית אינה זמינה; אפשר לייצא את המצב בקובץ JSON.';}
const boxes=[...document.querySelectorAll('[data-task]')];
boxes.forEach(b=>{if(typeof saved[b.dataset.task]==='boolean')b.checked=saved[b.dataset.task];b.addEventListener('change',()=>{saved[b.dataset.task]=b.checked;try{localStorage.setItem(storageKey,JSON.stringify(saved));}catch(e){document.querySelector('#storage-note').textContent='לא ניתן לשמור בדפדפן זה; ייצא את המצב לשמירתו.';}progress();});});
function progress(){document.querySelector('#progress').textContent=boxes.filter(b=>b.checked).length+' מתוך '+boxes.length+' מסומנות';}progress();
document.querySelector('#export').addEventListener('click',()=>{const state={project:'ParshaPulse',version:'0.0.2',exported_at:new Date().toISOString(),tasks:Object.fromEntries(boxes.map(b=>[b.dataset.task,b.checked]))};const u=URL.createObjectURL(new Blob([JSON.stringify(state,null,2)],{type:'application/json;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='ParshaPulse-task-status.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
'''
htmltext='''<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="מעבדת פרשת השבוע — 28 אלגוריתמים, תבניות ומסלול לימוד"><title>ParshaPulse — מעבדת פרשת השבוע</title><style>'''+css+'''</style></head><body><a class="skip" href="#content">דילוג לתוכן</a><header><div><h1>📖 מעבדת פרשת השבוע · ParshaPulse</h1><p>הפרשה פוגשת את פעימת החיים</p><button id="version" class="badge" type="button" aria-haspopup="dialog">גרסה 0.0.2 · יומן עדכונים</button></div><div class="actions"><button id="task-button" type="button">✅ 120 משימות</button><button id="about-button" type="button" aria-haspopup="dialog">✍️ אודות</button><button id="print" type="button">🖨️ הדפסת המקטע</button></div></header><div class="layout"><aside aria-label="ניווט מסמכים"><label for="search">🔎 חיפוש במאגר</label><input id="search" type="search" placeholder="נושא, אלגוריתם או מילה · Ctrl+K"><p id="results" role="status" aria-live="polite">'''+str(len(paths))+''' מסמכים</p><nav>'''+''.join(nav)+'''</nav></aside><main id="content">'''+''.join(articles)+'''<article id="tasks-view" tabindex="-1"><h1>✅ מפת המשימות</h1><p class="note">צילום המצב ההתחלתי תואם ל־TODO.md. שינויים כאן נשמרים בדפדפן הנוכחי בלבד ואינם עורכים קבצי מקור.</p><p id="storage-note">אפשר לייצא את הסימונים לקובץ JSON לשמירת צילום מצב.</p><p id="progress" role="status" aria-live="polite"></p><button id="export" class="tool" type="button">📥 ייצוא מצב משימות</button>'''+''.join(taskhtml)+'''</article></main></div><dialog id="versions" aria-labelledby="version-title"><button class="close" type="button" aria-label="סגירת יומן הגרסאות">✕ סגירה</button><h1 id="version-title">🪧 גרסאות ועדכונים</h1>'''+render((ROOT/'CHANGELOG.md').read_text(encoding='utf-8'),'CHANGELOG.md')+'''</dialog><dialog id="about" aria-labelledby="about-title"><button class="close" type="button" aria-label="סגירת אודות">✕ סגירה</button><h1 id="about-title">✍️ אודות ParshaPulse</h1>'''+render((ROOT/'CREDITS.md').read_text(encoding='utf-8'),'CREDITS.md')+'''</dialog><footer>כ׳ בחשון תשפ״ז · 31.10.2026 · שעת הבנייה ב־project.json · Cyber Shamanic / AnLoMinus · אוֹרָקֵס<br>״כְּשֶׁאָדָם אוֹמֵר חִדּוּשֵׁי אוֹרַיְתָא, עַל יְדֵי זֶה מְשַׂמֵּחַ אֶת הַשֵּׁם יִתְבָּרַךְ.״ — ספר המידות, לימוד א׳, ג׳.</footer><script>'''+script+'''</script></body></html>'''
(ROOT/'START-HERE.html').write_text(htmltext,encoding='utf-8')
print(json.dumps({'embedded_documents':len(paths),'bytes':len(htmltext.encode()),'tasks':len(tasks)}))
