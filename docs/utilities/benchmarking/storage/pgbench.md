# pgbench

[pgbench](https://www.postgresql.org/docs/current/pgbench.html) — утилита тестирования производительности PostgreSQL путём многократного выполнения заданной последовательности команд.

Входит в стандартный набор программ PostgreSQL, поэтому работает на всех стандартных ОС при наличии созданной базы данных.

pgbench способен тестировать либо специальные таблицы для оценки эффективности базы данных, либо пользовательские таблицы.

В первом случае необходимо провести инициализацию специальных таблиц:

* pgbench_accounts
* pgbench_branches
* pgbench_history
* pgbench_tellers

с помощью вызова pgbench с параметром -i

```bash
pgbench -i db_name

dropping old tables...
creating tables...
generating data...
100000 of 100000 tuples (100%) done (elapsed 0.01 s, remaining 0.00 s)
vacuuming...
creating primary keys...
done.
```

Пример тестирования базы данных и созданных таблиц (сокращённый вывод):

```bash
pgbench -c 20 -j 2 -T 30 -r db_name

number of clients: 20
number of threads: 2
duration: 30 s
number of transactions actually processed: 37474
latency average = 16.023 ms
tps = 1248.215314 (including connections establishing)
```

Для тестирования собственных таблиц, можно пропустить инициализацию, передав в качестве параметра файл с инструкциями для утилиты.

Скрипт для тестирования:

```
\set car_id random(1, 100)

SELECT * FROM car WHERE car_id = :car_id;

SELECT * FROM car WHERE brand = 'BMW' AND color = 'Синий';
```

Вызов команды (сокращённый вывод):

```bash
pgbench -f test.sql -c 20 -T 30 -r car_station

transaction type: test.sql
number of clients: 20
duration: 30 s
number of transactions actually processed: 645415
latency average = 0.854 ms
latency stddev = 0.228 ms
tps = 21513.140976 (including connections establishing)
statement latencies in milliseconds:
         0.001  \set car_id random(1, 100)
         0.423  SELECT * FROM car WHERE car_id = :car_id;
         0.430  SELECT * FROM car WHERE brand = 'BMW' AND color = 'Синий';
```

За счёт подробной статистики по выполненным запросам, можно выявить наиболее неэффективные среди них.
