#!/usr/bin/env python3
"""Portable entry: no teacher path, fixed port, dependencies, or credentials."""
import argparse
from pathlib import Path
import sys

def main():
    if sys.version_info < (3, 10):
        raise SystemExit("需要Python 3.10或更新版本，请让WorkBuddy检查环境后打开。")
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, default=root / '我的工作台')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(root / '素材工作台'))
    from server import Server
    from workspace import Workspace
    import json
    import webbrowser
    server = Server(Workspace(args.project), args.port)
    url = 'http://127.0.0.1:%s/' % server.server_port
    print(json.dumps({'url': url, 'project': str(args.project.resolve())}, ensure_ascii=False), flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
