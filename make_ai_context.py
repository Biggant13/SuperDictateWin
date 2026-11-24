import json
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
                filepath = os.path.join(root, f)
                loc = ""
                if f.endswith(".py"):
                    try:
                        with open(filepath, "r", encoding="utf-8") as py_f:
                            loc = f" ({len(py_f.readlines())} loc)"
                    except:
                        pass
                tree_str += f'{subindent}{f}{loc}\n'
    return tree_str

def extract_api(filepath):
    """Вытаскивает классы, функции, докстринги и глобальные константы."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            
        api = []
        for node in tree.body:
            # Глобальные константы (например, MAX_RECORDS = 100)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, (ast.Constant, ast.List, ast.Dict, ast.Set)):
                    target_name = node.targets[0].id
                    if target_name.isupper():  # Берем только КАПС
                        api.append(f"{target_name} = ...")

            # Классы
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                doc_str = f"  # {doc.splitlines()[0]}" if doc else ""
                api.append(f"class {node.name}:{doc_str}")
                
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        args = [a.arg for a in child.args.args]
                        c_doc = ast.get_docstring(child)
                        c_doc_str = f"  # {c_doc.splitlines()[0]}" if c_doc else ""
                        api.append(f"    def {child.name}({', '.join(args)}){c_doc_str}")
            
            # Функции
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                doc = ast.get_docstring(node)
                doc_str = f"  # {doc.splitlines()[0]}" if doc else ""
                api.append(f"def {node.name}({', '.join(args)}){doc_str}")
                
        return "\n".join(api)
    except Exception as e:
        return f"[Ошибка парсинга: {e}]"

def get_git_info():
    """Вытаскивает текущую ветку и последний коммит."""
    import subprocess
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], encoding="utf-8").strip()
        last_commit = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], encoding="utf-8").strip()
        return f"Ветка: `{branch}` | Последний коммит: *{last_commit.splitlines()[0]}*"
    except Exception:
        return "Git информация недоступна."

def get_config_json():
    """Читает config.json, чтобы ИИ знал доступные настройки."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Скрываем потенциально длинные/секретные данные, оставляем только ключи и примитивы
            safe_cfg = {k: v for k, v in cfg.items() if isinstance(v, (str, int, float, bool, list))}
            return json.dumps(safe_cfg, indent=2, ensure_ascii=False)
    except Exception:
        return "{}"

def generate_context():
    version = get_version()
    tree = get_tree(".")
    reqs = get_requirements()
    git_info = get_git_info() # <--- НОВОЕ
    config_data = get_config_json() # <--- НОВОЕ

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

    config_block = f"```json\n{config_data}\n```\n"
    
    context = f"""# Контекст проекта: {PROJECT_NAME}

**Ссылка на репозиторий GitHub:** {REPO_URL}
**Текущий статус:** {git_info}

Ты — Senior Python-разработчик. Ты помогаешь вайб-кодеру (пользователю) разрабатывать приложение **{PROJECT_NAME}** (версия {version}). 
Приложение представляет собой офлайн-диктовку: нажимаешь хоткей -> записывается звук -> распознается нейросетью GigaAM v3 -> вставляется текст.

## ⚙️ Текущий config.json (Доступные настройки)
{config_block}

## 📦 Зависимости (requirements.txt)
{reqs_block}

## 📂 Структура проекта
{tree_block}

# --- ВСТАВИТЬ ПОСЛЕ ЭТОЙ СТРОКИ ---
## 🎮 Управление и ключевые фичи
1. **F9 (Диктовка с микрофона):** Нажатие и удержание. Записывает голос с микрофона, распознает через GigaAM и вставляет текст в активное окно. Добавляет слова в статистику.
2. **F8 (Диктовка с системы):** Нажатие и удержание. Записывает системный звук (loopback), распознает и вставляет текст. Добавляет слова в статистику.
3. **F7 (Режим встреч):** Переключатель (нажал — старт, нажал — стоп). Пишет одновременно микрофон и систему. Сохраняет результат в папку `meetings/` (файлы `.txt`), **не вставляет текст в окно и не добавляет в статистику**. Перед началом записи в файл вписывается активный «Промт» (из `config.json` -> `meeting_prompts`).
4. **История (Трей -> Распознавания):** Окно с историей. Поддерживает «Избранное» (желтый фон, не удаляется при очистке), удаление по одной записи и фильтр «Только избранные».
5. **Менеджер промтов (Трей -> Промт):** Окно для создания/редактирования/удаления промтов. Выбранный промт (галочка ✅) используется для F7.
6. **Сплэш-скрин:** Работает в отдельном `multiprocessing.Process` (чтобы анимация пульсации не зависала из-за GIL при загрузке ONNX-модели).
7. **Статистика:** Считает только слова, надиктованные через F8 и F9. Встречи (F7) не учитываются.

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