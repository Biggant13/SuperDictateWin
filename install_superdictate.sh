#!/bin/bash

# --- Цвета для вывода ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}--- Установка SuperDictate для Linux ---${NC}"

# 1. Проверка зависимостей
echo -e "\n${YELLOW}Шаг 1: Проверка системных зависимостей...${NC}"
for cmd in curl tar; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Ошибка: $cmd не установлен. Установите его (например: sudo apt install $cmd)${NC}"
        exit 1
    fi
done
echo "Базовые утилиты найдены."

# Проверка прав sudo (нужны для добавления в группу)
if ! sudo -v; then
    echo -e "${RED}Ошибка: скрипту требуются права sudo для настройки прав доступа.${NC}"
    exit 1
fi

# 2. Определение последней версии
echo -e "\n${YELLOW}Шаг 2: Поиск последней версии на GitHub...${NC}"
REPO="Biggant13/SuperDictateWin"
LATEST_TAG=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_TAG" ]; then
    echo -e "${RED}Не удалось определить последнюю версию. Проверьте интернет или лимиты GitHub API.${NC}"
    exit 1
fi
echo "Найдена версия: $LATEST_TAG"

# 3. Скачивание и распаковка
echo -e "\n${YELLOW}Шаг 3: Скачивание и установка...${NC}"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/SuperDictate-Linux.tar.gz"
INSTALL_DIR="$HOME/.local/share/SuperDictate"

# Создаем временную директорию
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Скачивание архива..."
if ! curl -L -o "$TMP_DIR/SuperDictate.tar.gz" "$DOWNLOAD_URL"; then
    echo -e "${RED}Ошибка скачивания. Проверьте доступность релиза: $DOWNLOAD_URL${NC}"
    exit 1
fi

echo "Установка в $INSTALL_DIR..."
# Если папка уже есть, удаляем старую версию перед распаковкой
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
tar -xzf "$TMP_DIR/SuperDictate.tar.gz" -C "$INSTALL_DIR" --strip-components=1

# 4. Создание ярлыка для меню приложений
echo -e "\n${YELLOW}Шаг 4: Создание ярлыка в меню...${NC}"
DESKTOP_FILE="$HOME/.local/share/applications/superdictate.desktop"
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=SuperDictate
Comment=Local offline dictation
Exec=$INSTALL_DIR/SuperDictate
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;Audio;Accessibility;
EOF
# Делаем ярлык исполняемым (на всякий случай)
chmod +x "$DESKTOP_FILE"
echo "Ярлык создан."

# 5. Настройка прав для evdev (Wayland)
echo -e "\n${YELLOW}Шаг 5: Настройка прав для работы в Wayland...${NC}"
if groups "$USER" | grep -q "\binput\b"; then
    echo "Пользователь $USER уже состоит в группе 'input'."
else
    echo "Добавление пользователя $USER в группу 'input' (требуются права sudo)..."
    sudo usermod -aG input "$USER"
    echo -e "${GREEN}Готово!${NC}"
    NEED_RELOGIN=1
fi

echo -e "\n${GREEN}--- Установка успешно завершена! ---${NC}"
echo -e "Вы можете найти SuperDictate в меню приложений."
if [ -n "$NEED_RELOGIN" ]; then
    echo -e "${RED}ВАЖНО: Вы должны выйти из системы и войти снова, чтобы права на чтение клавиатуры вступили в силу!${NC}"
fi