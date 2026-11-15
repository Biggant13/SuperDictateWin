import os
import ast

PROJECT_NAME = "SuperDictateWin"
REPO_URL = "https://github.com/Biggant13/SuperDictateWin" 

def get_version():
    try:
        with open("core/version.py", "r", encoding="utf-8") as f:
            for line in f:
                if "__version__" in line:
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"

def get_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "Не найден requirements.txt"

def get_tree(startpath):
    tree_str = ""
    ignore_dirs = {'.git', 'venv', '__pycache__', 'dist', 'build', '_internal', 'gigaam-v3-e2e-rnnt-onnx'}
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        level = root.replace(startpath, '').count(os.sep)
        if level > 3: continue
        indent = '    ' * level
        tree_str += f'{indent}{os.path.basename(root)}/\n'
        subindent = '    ' * (level + 1)
        for f in files:
            if f.endswith(('.py', '.txt', '.json', '.spec', '.iss', '.md', '.yml')):
                tree_str += f'{subindent}{f}\n'
    return tree_str

def extract_api(filepath):
    """Вытаскивает классы и функции из Python-файла, чтобы ИИ знал API."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            
        api = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                api.append(f"class {node.name}:")
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        args = [a.arg for a in child.args.args]
                        api.append(f"    def {child.name}({', '.join(args)})")
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                api.append(f"def {node.name}({', '.join(args)})")
        return "\n".join(api)
    except Exception as e:
        return f"[Ошибка парсинга: {e}]"

def generate_context():
    version = get_version()
    tree = get_tree(".")
    reqs = get_requirements()
    
    # Читаем правила, если пользователь их создал
    rules = ""
    if os.path.exists("AI_RULES.md"):
        with open("AI_RULES.md", "r", encoding="utf-8") as f:
            rules = f.read().strip()
    else:
        rules = "Особых правил нет. Следуй общей архитектуре проекта."

    # Вытаскиваем API из ключевых файлов
    api_docs = ""
    for root, _, files in os.walk("core"):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                path = os.path.join(root, f)
                api_docs += f"\n### {path}\n```python\n{extract_api(path)}\n```\n"
                
    api_docs += f"\n### main.py\n```python\n{extract_api('main.py')}\n```\n"

    tree_block = "```text\n" + tree + "```\n"
    reqs_block = "```text\n" + reqs + "\n```\n"
    
    context = f"""# Контекст проекта: {PROJECT_NAME}

**Ссылка на репозиторий GitHub:** {REPO_URL}

Ты — Senior Python-разработчик. Ты помогаешь вайб-кодеру (пользователю) разрабатывать приложение **{PROJECT_NAME}** (версия {version}). 
Приложение представляет собой офлайн-диктовку: нажимаешь хоткей -> записывается звук -> распознается нейросетью GigaAM v3 -> вставляется текст.

## 📦 Зависимости (requirements.txt)
{reqs_block}

## 📂 Структура проекта
{tree_block}

## 🏗 Архитектура и правила (НЕ ЛОМАТЬ!)
1. **Потоки (Threading):** Обработчики `pynput` (`on_press`, `on_release`) работают в системном потоке хука Windows. Они **обязаны** завершаться мгновенно (до 300 мс). Вся тяжелая работа вынесена в `task_queue`.
2. **Хоткеи (HotkeyManager):** Логика нажатий изолирована в `core/hotkey.py`. **Никогда не переноси фильтрацию клавиш обратно в `main.py`**. Это защищает от залипания клавиш.
3. **Аудио (AudioRecorder):** `audio.stop()` возвращает `True/False`. Остановка `InputStream` вынесена в отдельный поток (иначе PortAudio вешает приложение).
4. **Пути (Paths):** В `config.py` используется `sys.executable` для собранных версий. Конфиги лежат рядом с `.exe`.
5. **Формат выдачи кода (КРИТИЧЕСКИ ВАЖНО):** Никогда не выдавай весь файл целиком, если об этом не просят. Выдавай только измененный участок. Всегда четко указывай, куда именно его вставить, используя следующий шаблон:
```python
# --- СТРОКА СВЕРХУ (найди её в файле) ---
# --- ВСТАВИТЬ ПОСЛЕ ЭТОЙ СТРОКИ ---
[твой новый код]
# --- КОНЕЦ ВСТАВКИ ---
# --- СТРОКА СНИЗУ (убедись, что она осталась) ---
6. **Релизы (CI/CD):** На GitHub уже настроен GitHub Actions. Сборка релизов (`.exe` и `.tar.gz`) происходит **автоматически** при пуше тега. **Никогда не объясняй пользователю, как создавать релиз на GitHub вручную** (никаких "Draft a new release", "Choose a tag" и т.д.). Просто скажи выполнить `git tag` и `git push origin <tag>`.
7. **Дополнительные правила от пользователя:**
{rules}

## 🧩 Карта API (Что уже реализовано в коде)
Ниже приведены реальные классы и методы. Используй только их, не выдумывай новые функции, если они уже есть.
{api_docs}
"""
    
    # Удаляем старый файл, если он существует (чтобы избежать конфликтов в Windows)
    if os.path.exists("AI_CONTEXT.md"):
        try:
            os.remove("AI_CONTEXT.md")
        except Exception as e:
            print(f"⚠️ Не удалось удалить старый AI_CONTEXT.md (возможно, он открыт в редакторе): {e}")

    with open("AI_CONTEXT.md", "w", encoding="utf-8") as f:
        f.write(context)
    print("✅ Файл AI_CONTEXT.md успешно перезаписан! (Вся структура и API подтянуты автоматически)")

if __name__ == "__main__":
    generate_context()