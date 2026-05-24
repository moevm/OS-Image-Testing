# Руководство по созданию и использованию бэкапов для metabase

В этом рукводстве расписаны основные шаги для создания бэкапов запущенного сервиса metabase, а также переноса его на другие системы с последующей инциализацией.

## Создание бэкапов

**Metabase** поднимается вместе со своей дополнительной базой данных, где хранит все данные для входа, а также данные о графиках и дашбордах.

Для того чтобы сделать бэкап у вас должна быть запущена эта БД `os-image-testing-imgtests-metabase-meta-db-1`.

Далее выполните команду в терминале:

```bash
docker exec os-image-testing-imgtests-metabase-db-1 pg_dump -U metabase -d metabase -F c -b -v > metabase_backup_$(date +%Y%m%d).dump
```

После выполнения этой команды в текущей директории создастся дамп БД metabase *(пр. metabase_backup_20260407.dump)*. Далее можно передать его другому разработчику. Также, не забудьте передать ему данные для входа на сайт.

## Импорт бэкапа

Предположим, у вас есть файл дампа metabase_backup.dump, который Вы положили в папку с проектом, а также данные для входа.

### **Шаг 1. Запустите проект**

```bash
make docker-run-metabase
```

### **Шаг 2. Остановите контейнер metabase**

```bash
docker stop os-image-testing-imgtests-metabase-1
```

### **Шаг 3. Очистите текущую пустую базу**

Так как Metabase при первом старте уже успел создать пустые таблицы, их надо удалить, чтобы не было конфликтов при восстановлении.

```bash
docker exec -i os-image-testing-imgtests-metabase-meta-db-1 psql -U metabase -d postgres -c "DROP DATABASE metabase;"

docker exec -i os-image-testing-imgtests-metabase-meta-db-1 psql -U metabase -d postgres -c "CREATE DATABASE metabase;"
```

### **Шаг 4. Запишите дамп в базу**

```bash
docker exec -i os-image-testing-imgtests-metabase-meta-db-1 pg_restore -U metabase -d metabase < ваш_дамп_файл.dump
```

### **Шаг 5. Снова запустите Metabase**

```bash
docker start os-image-testing-imgtests-metabase-1
```

У вас поднимется заполненный **metabase** со всеми графиками и дашбордами.

## Полезные ссылки

* [Руководство по созданию дампов БД metabase](https://www.mintlify.com/metabase/metabase/operations/backing-up)

* [Установка metabase в production](https://www.metabase.com/docs/latest/installation-and-operation/running-metabase-on-docker#production-installation)
