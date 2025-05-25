Структура проекта:
bbline/
├── ingest/                  # загрузка и парсинг рук
│   └── ggpoker_import.py
├── parse/                   # выделение данных из рук
│   └── hand_parser.py
├── database/
│   └── bbline.sqlite
├── analysis/                # анализ раздач
│   └── analyzer.py
├── replayer/                # покерный реплеер (raw MVP)
│   └── replay_one.py
├── export/
│   └── generate_json.py     # экспорт дампа в JSONL
├── assets/                  # тестовые раздачи
│   └── test_hand_01.txt
├── main.py                  # точка входа
└── requirements.txt


TODO
Дальше
hand_parser.py — превращаем текст GG-hand в hands, seats, actions.

batch_import.py — жмёт 1000 файлов .txt за раз.

rebuild_computed.py — агрегирует нужные флаги после импорта.