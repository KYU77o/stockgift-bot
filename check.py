import ast
import traceback

files = ['app.py', 'services/scheduler.py', 'services/scraper.py', 'utils/flex.py']
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            ast.parse(file.read())
            print(f"OK: {f}")
    except SyntaxError as e:
        print(f"SyntaxError in {f}: {e}")
        traceback.print_exc()
