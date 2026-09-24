#!/usr/bin/env python3
"""Publish one Markdown file as a Confluence page.

    set -a; . ./.env.confluence.local; set +a
    ../communication/xlenv/bin/python tools/confluence_md.py <file.md> --title "Page title" \\
        [--parent 3761831940] [--attach file ...] [--build-only]

The first h1 in the file becomes a bold lead line (the page title is --title).
Links to Confluence pages can be written in the Markdown as
[text](confluence:Page Title) and are turned into page links.
"""
import argparse, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from confluence_export import Confluence, validate, esc_attr  # noqa: E402
from confluence_evidence import md_to_storage, esc  # noqa: E402


class P:
    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file')
    ap.add_argument('--title', required=True)
    ap.add_argument('--parent', default=os.environ.get('CONFLUENCE_PARENT_ID'))
    ap.add_argument('--attach', nargs='*', default=[])
    ap.add_argument('--build-only', action='store_true')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'confluence-md'))
    args = ap.parse_args()

    text = open(args.file, encoding='utf-8').read()
    # [text](confluence:Title) -> page link (kept through conversion as an https placeholder)
    text = re.sub(r'\]\(confluence:([^)]+)\)', lambda m: '](https://confluence.local/' + m.group(1).replace(' ', '%20') + ')', text)
    body, h1 = md_to_storage(text)
    body = re.sub(r'<a href="https://confluence\.local/([^"]+)">(.*?)</a>',
                  lambda m: f'<ac:link><ri:page ri:content-title="{esc_attr(m.group(1).replace("%20", " "))}"/>'
                            f'<ac:link-body>{m.group(2)}</ac:link-body></ac:link>', body)
    if h1 and h1 != args.title:
        body = f'<p><b>{esc(h1)}</b></p>' + body
    page = P()
    page.key, page.body = re.sub(r'[^a-z0-9]+', '-', args.title.lower()).strip('-'), body
    validate(page)
    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, page.key + '.xml')
    open(out, 'w', encoding='utf-8').write(body)
    print(f'built {out} ({len(body)//1024} KB)')
    if args.build_only:
        return
    base, email, token = (os.environ.get(k) for k in ('CONFLUENCE_BASE', 'CONFLUENCE_EMAIL', 'CONFLUENCE_TOKEN'))
    if not (base and email and token and args.parent):
        sys.exit('publish needs CONFLUENCE_BASE, CONFLUENCE_EMAIL, CONFLUENCE_TOKEN and --parent / CONFLUENCE_PARENT_ID')
    cf = Confluence(base, email, token)
    space_id = cf.page(args.parent)['spaceId']
    pid, what = cf.upsert(space_id, args.parent, args.title, body)
    existing = cf.attachments(pid) if args.attach else {}
    for path in args.attach:
        try:
            cf.attach(pid, os.path.basename(path), path, existing)
        except RuntimeError as e:
            print(f'  WARNING attachment {path}: {e}')
    try:
        cf.set_full_width(pid)
    except RuntimeError as e:
        print(f'  WARNING full width: {e}')
    print(f'{what} {args.title} -> {base}/wiki/spaces/TS/pages/{pid}')


if __name__ == '__main__':
    main()
