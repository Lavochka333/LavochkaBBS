"""Сохраняет очередь в тот же маршрут, откуда она читается.

Проверено: GET /api/devices/<key>/queue отдаёт items, а POST того же маршрута
ждёт {items: [...]}. Прежний код писал в /api/queue - это другой, глобальный
список, который остаётся пустым при обычной работе одного устройства. То есть
правки из раздела просто исчезали.
"""
import io
from pathlib import Path

PATH = Path("static/js/studio.js")
src = PATH.read_text(encoding="utf-8")

OLD = """        if (target.id === 'saveQueue') {
            try {
                await api('/api/queue', { method: 'PUT', body: { queue: queueData.queue } })
                    .catch(async () => {
                        await api('/api/queue', { method: 'POST', body: queueData.queue });
                    });
                toast('Очередь сохранена', 'ok');
                await loadQueue();
            } catch (error) {
                toast('Не удалось сохранить: ' + error.message, 'error');
            }
            return;
        }"""

NEW = """        if (target.id === 'saveQueue') {
            if (!settingsKey) {
                toast('Сначала подключите устройство', 'error');
                return;
            }
            try {
                await api(`/api/devices/${encodeURIComponent(settingsKey)}/queue`, {
                    method: 'POST',
                    body: { items: queueData.queue },
                });
                toast('Очередь сохранена', 'ok');
                await loadQueue();
            } catch (error) {
                toast('Не удалось сохранить: ' + error.message, 'error');
            }
            return;
        }"""

assert src.count(OLD) == 1, f"сохранение очереди: {src.count(OLD)}"
src = src.replace(OLD, NEW)

# Очереди нужен ключ устройства; берём его при загрузке раздела.
OLD_LOAD = """        const devices = await api('/api/devices');
        const first = (devices.devices || [])[0];
        if (!first) {
            queueData = { queue: [], brawlers: [] };
            renderQueue();
            return;
        }"""
NEW_LOAD = """        const devices = await api('/api/devices');
        const first = (devices.devices || [])[0];
        if (!first) {
            queueData = { queue: [], brawlers: [] };
            renderQueue();
            return;
        }
        settingsKey = first.key;"""
assert src.count(OLD_LOAD) == 1, f"загрузка очереди: {src.count(OLD_LOAD)}"
src = src.replace(OLD_LOAD, NEW_LOAD)

PATH.write_text(src, encoding="utf-8")
print("сохранение очереди переведено на маршрут устройства")
