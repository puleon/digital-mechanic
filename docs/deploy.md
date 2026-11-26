# Развёртывание на стенде

Стенд: Ubuntu 24.04, Docker 29 + Compose, Caddy как reverse proxy с автоматическим
HTTPS. Приложение и моки живут в одном compose-проекте, наружу открыт только API
на `127.0.0.1:8090`.

## 1. Код и данные

```bash
git clone https://github.com/puleon/digital-mechanic.git ~/digital-mechanic
cd ~/digital-mechanic

# PDF руководств не входят в git — кладём рядом с проектом
mkdir -p manuals
scp <локальные PDF> shevek:~/digital-mechanic/manuals/

# секреты
scp .env shevek:~/digital-mechanic/.env   # затем chmod 600
```

В `.env` на сервере: `LLM_API_KEY`, `LLM_MODEL`, адреса моков (в compose они
переопределяются на имена сервисов).

## 2. Запуск

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8090/api/health
```

При первом старте entrypoint собирает индекс по PDF в `data/index/`. Повторный
запуск индекс не пересобирает; после замены PDF удалить `data/index/` и перезапустить.

Обновление после `git push`:

```bash
git pull
docker compose up -d --build api    # пересобирает только приложение
```

## 3. Caddy

Добавить в `/etc/caddy/Caddyfile` блок из `deploy/Caddyfile.snippet`:

```
digital-mechanic.128-0-134-250.sslip.io {
	encode zstd gzip
	reverse_proxy 127.0.0.1:8090
}
```

Проверить и перезагрузить:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy сам выпускает сертификат Let's Encrypt (домен sslip.io указывает на IP стенда).
Проверка: `curl https://digital-mechanic.128-0-134-250.sslip.io/api/health`.

## 4. Диагностика

```bash
docker compose logs -f api          # старт, ошибки LLM и моков
docker compose logs -f mock_ml
docker compose exec api python -c "import app.rag.tools as t; print(t.allowed_manuals('ЯМЗ-236М2'))"
```

Если LLM недоступна, `/api/chat` вернёт ошибку в UI, остальные экраны (парк, карточка
ТС, история) продолжают работать. Индекс и SQLite лежат в `data/` и переживают
перезапуск контейнеров.
