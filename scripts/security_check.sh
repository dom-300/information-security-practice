#!/usr/bin/env bash
set -u

OUT="reports/security_check.txt"
mkdir -p reports
echo "=== ЗПР-2 ПЕРЕВІРКА КОНФІГУРАЦІЇ ТА СЕРЕДОВИЩА ($(date -u +'%Y-%m-%d %H:%M:%S UTC')) ===" | tee "$OUT"

FAILS=0
WARNS=0
PASS=0

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "[PASS] $name" | tee -a "$OUT"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $name" | tee -a "$OUT"
        FAILS=$((FAILS + 1))
    fi
}

warn_check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "[PASS] $name" | tee -a "$OUT"
        PASS=$((PASS + 1))
    else
        echo "[WARN] $name" | tee -a "$OUT"
        WARNS=$((WARNS + 1))
    fi
}

echo -e "\n--- 1. Секрети та Git ---" | tee -a "$OUT"
check "Файл .env відсутній у Git" "! git ls-files | grep -E '(^|/)\.env$'"
check "Сертифікати та ключі відсутні у Git" "! git ls-files | grep -E '\.(key|crt|pem)$'"
check "Бази даних та бекапи відсутні у Git" "! git ls-files | grep -E '\.(db|db\.enc)$'"
check "Fail-fast у app/config.py (без дефолтного JWT_SECRET_KEY)" "! grep -E 'os\.getenv\(\"JWT_SECRET_KEY\",\s*\"[^\"]+\"\)' app/config.py"

echo -e "\n--- 2. Шифрування та цілісність даних ---" | tee -a "$OUT"
check "У таблиці users відсутня колонка email" "docker compose exec -T api python -c \"import sqlite3; con=sqlite3.connect('data/app.db'); cols=[r[1] for r in con.execute('PRAGMA table_info(users)')]; exit(0 if 'email' not in cols and 'encrypted_email' in cols else 1)\""
check "Дані email у БД починаються з Fernet префіксу gAAAA" "docker compose exec -T api python -c \"import sqlite3; r=sqlite3.connect('data/app.db').execute('SELECT encrypted_email FROM users LIMIT 1').fetchone(); exit(0 if r and r[0].startswith('gAAAA') else 1)\""

echo -e "\n--- 3. Гарденінг контейнера та Nginx ---" | tee -a "$OUT"
check "Контейнер API працює від non-root (UID 1000)" "[ \"\$(docker compose exec -T api id -u | tr -d '\r\n')\" = '1000' ]"
check "Файлова система API у режимі read-only" "! docker compose exec -T api sh -c 'touch /app_code/test_rw.txt 2>/dev/null'"
check "Порт API (8000) не виставлений назовні на 0.0.0.0" "! docker compose port api 8000 | grep -q '0.0.0.0'"
check "Nginx перенаправляє HTTP на HTTPS (301)" "curl -sI http://localhost/health | grep -q '301 Moved Permanently'"
check "Nginx приховує точну версію (Server: nginx)" "curl -ksI https://localhost/health | grep -qi '^Server: nginx$'"

echo -e "\n--- ПІДСУМОК ПЕРЕВІРКИ ---" | tee -a "$OUT"
echo "PASS: $PASS | WARN: $WARNS | FAIL: $FAILS" | tee -a "$OUT"

if [ "$FAILS" -gt 0 ]; then
    echo "СТАТУС: FAILED" | tee -a "$OUT"
    exit 1
else
    echo "СТАТУС: PASSED" | tee -a "$OUT"
fi
