# Утилиты для endurance тестирования: нагрузки, сбор метрик и агрегация информации

### Перечислены утилиты, которые можно использовать для взаимодействия с данными

#### Сборщики

| Утилита             | Назначение                                                                                                                           |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Prometheus**      | Сбор метрик и хранение их в базах данных.                                                                                            |
| **VictoriaMetrics** | Сбор метрик и хранение их в базах данных.                                                                                            |
| **sysstat**         | Сбор и запись данных различных компонентов системы.                                                                                  |

#### Визуализация данных из различных источников

| Утилита          | Назначение                                                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **Grafana**      | Визуализация данных из Prometheus или других источников.                                                                             |
| **netdata**      | Веб страничка для мониторинга всех аспектов системы в реальном времени с возможностью сохранения в базы данных.                      |
| **htop**         | Интерактивный диспетчер процессов в реальном времени, без сохранения истории.                                                        |
| **fio-plot**     | Визуализация результатов работы fio в виде графиков и диаграмм.                                                                      |

#### Создание нагрузки на различные части системы

| Утилита          | Назначение                                                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **stress-ng**    | Создание нагрузки на компоненты системы (CPU, диски, сеть, память).                                                                  |
| **fio**          | Создание синтетической нагрузки на диски.                                                                                            |
| **pgbench**      | Создание нагрузки, тестирование производительности баз данных.                                                                       |
| **vdbench**      | Создание нагрузки на системы хранения данных.                                                                                        |
| **SQLIOSim**     | Создание нагрузки на диски, приближенной к реальной.                                                                                 |

#### Логи и их анализ

| Утилита          | Назначение                                                                                                                           |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **journalctl**   | Просмотр и фильтрация системных логов, поиск ошибок.                                                                                 |
| **dmesg**        | Просмотр логов ядра Linux для диагностики ошибок системы, драйверов.                                                                 |
| **lnav**         | Анализ и навигация по логам с подсветкой синтаксиса.                                                                                 |

### Метрики, важные для endurance тестирования

- Температурные показатели

- Утечки памяти

- Отсутствие ошибок

- Стабильность системы

### Примеры использования

### 1. stress-ng

https://github.com/ColinIanKing/stress-ng

Стресс-тест и мониторинг дисков.

```
stress-ng --hdd 2 --timeout 1m & iostat -x 1
```

![iostat](https://github.com/user-attachments/assets/239b75cc-ff31-4679-9e9f-dda7b2c2561d)

### 2. htop

https://github.com/htop-dev/htop

Проверка на работоспособность процессов во время тестирования.

```
htop
```

![htop](https://github.com/user-attachments/assets/15818741-f2db-4ec3-9973-b83265b4f7b9)

### 3. sysstat

https://github.com/sysstat/sysstat

Анализ операций чтения и записи диска с помощью входящей утилиты **iostat** во время тестирования дисковых подсистем.

Детальная статистика по дискам каждые 5 секунд, 10 раз.

```
iostat -dxm 5 10
```

### 4. Prometheus + Grafana

https://github.com/prometheus/prometheus

https://grafana.com

Сбор данных о компонентах системы во время длительного тестирования с отслеживанием результатов тестов.

Мониторинг сетевых сетевого интерфейса.

```
*promql* rate(node_network_receive_errs_total{device="eth0"}[5m])
```

### 5. netdata

https://github.com/netdata/netdata

Мониторинг всех компонентов системы в реальном времени во время выполнения тестов.

```
sudo systemctl start netdata
```

Доступен по http://localhost:19999

![netdata](https://github.com/user-attachments/assets/ddfa30ae-7ba3-40f4-b907-55596c25bbc8)

### 6. journalctl + lnav

https://man.archlinux.org/man/journalctl.1.en

https://docs.lnav.org/en/v0.12.4

Поиск segfault в логах после выполнения тестов.

Просмотр логов за последний час.

```
journalctl --since "1 hour ago" | lnav
```

![journalctl](https://github.com/user-attachments/assets/88a7e172-d24a-4edc-99fc-ad7a5287f6f0)

### 7. dmesg + lnav

https://man7.org/linux/man-pages/man1/dmesg.1.html

Поиск ошибок ядра.

```
sudo dmesg -T -l err | lnav
```



# Тестирование подсистем Linux

## fwts

[Firmware Test Suite](https://github.com/fwts/fwts) (FWTS) — набор тестов, который выполняет проверку исправности прошивки.

Он предназначен для выявления ошибок BIOS, UEFI, ACPI и других систем, и объяснения причин неисправностей.

fwts нацелен в первую очередь  для диагностики неполадок Linux систем.

### Интеграция в Yocto

Все необходимые файлы находятся по пути `meta-openembedded/meta-oe/recipes-test/fwts/`.

Тесты можно подключить, добавив в конфигурацию название пакета:

```
IMAGE_INSTALL:append = " fwts"
```

Внутри образа можно прописать команду для запуска тестов:

```bash
fwts
```

В результате будет сформирован файл `results.log` с подробными результатами тестирования.

В файле также содержатся все полученные ошибки, их краткое описание и информация по тестам, записанная в таблицу.

<img width="491" height="335" alt="image" src="https://github.com/user-attachments/assets/3d8e4988-d99a-42b9-b4fb-7992398012b5" />

## syzkaller

[syzkaller](https://github.com/google/syzkaller) — автоматизированная система "фаззинга" для ядра Linux.

Непрерывно обрабатывает большое количество случайных программ / входных данных, чтобы вызвать сбои или ошибки (для их выявления).

В процессе работы находит ошибки ядра, утечки памяти, переполнение данных и так далее.

Покрывает следующие подсистемы: `сеть`, `файловые системы`, `память`, а также используется для `драйверов`.

### Интеграция в Yocto

Находится там же, где fwts, по пути `meta-openembedded/meta-oe/recipes-test/syzkaller`.

Тесты подключаются через конфигурацию:

```
IMAGE_INSTALL:append = " syzkaller"
```

Внутри образа бинарные файлы находятся по пути `/usr/bin/linux_*/`.

Если в образе подключена работа с сетью и есть syz-manager, то можно воспользоваться следующей командой для передачи статистики на localhost:

```bash
./usr/bin/linux_amd64/syz-manager -config my.cfg
```

[Пример конфигурации](https://github.com/google/syzkaller/blob/master/pkg/mgrconfig/testdata/qemu-example.cfg)

В конфигурации можно задать нагрузку: выделить больше ресурсов процессора, памяти или увеличить число процессов.

Для минимального теста без web-интерфейса можно создать подобный файл:

test.txt

```
mmap(&(0x7f0000000000)=nil, 0x1000, 0x3, 0x32, 0xffffffffffffffff, 0x0)
getpid()
openat(0xffffffffffffff9c, &(0x7f0000001000)="./file", 0x42, 0x1ff)
```

И запустить код:

```bash
./usr/bin/linux_amd64/syz-execprog -executor ./usr/bin/linux_amd64/syz-executor test.txt
```

## LTP

[LTP](https://github.com/linux-test-project/ltp) (Linux test project) - обширный набор тестов для тестирования ядра Linux и связанных с ним функций для проверки стабильности и надёжности.

Установка:

```bash
git clone --recurse-submodules https://github.com/linux-test-project/ltp.git
cd ltp
make autotools
./configure
```

Тесты находятся в папке **testcases/**

Их можно использовать для проверки работоспособности практически любых компонентов системы.

Подробное описание тестов в [документации](https://linux-test-project.readthedocs.io/en/latest/users/test_catalog.html).

### Интеграция в Yocto

LTP нет в стандартных слоях, но его можно добавить, написав собственный рецепт.

## Системные вызовы

### Метрики

- Количество вызовов

- Процент ошибок

### Создание нагрузки

Для создания нагрузки и проверки работоспособности можно использовать утилиту [stress-ng](https://github.com/ColinIanKing/stress-ng).

Пример работы:

```bash
stress-ng --sysinfo 10 --sysinfo-ops 10000
```

### Отслеживание ошибок

**strace** - утилита для отслеживания системных вызовов и сигналов.

Она помогает находить ошибки в работе программ, показывая статистику по тому, какие системные вызовы выполняются и какие ошибки возвращаются.

Пример работы:

```bash
strace -c -f -o trace.log ./test
```

## IPC

К механизмам IPC относят:

- Сигналы
- Каналы
- Сокеты
- Семафоры
- Разделённую память
- Очередь сообщений

### Метрики

- Пропускная способность (количество сообщений, которое ядро или процесс способно обработать)

- Задержки (время между отправкой сообщения одним потоком и его получения другим)

- Процент ошибок (потерянные, повторные сообщения)

### LTP тесты

Тесты лежат в testcases/kernel/syscalls/

- kill, sigaction

- socket, bind, sendmsg

- semget, semop в syscalls/ipc/

- shmget, shmat в syscalls/ipc/

- msgget, msgsnd в syscalls/ipc/

### Мониторинг стабильности

Для мониторинга работоспособности и стабильности IPC можно воспользоваться упомянутой выше **strace** или следующими утилитами:

- **ipcs** для семафоров, разделённой памяти и очередей сообщений

- **ss** для сокетов

- ```lsof | grep FIFO``` для списка открытых каналов

## Виртуальная память

### Метрики

- Используемая оперативная память

- Процент ошибок, неправильных аллокаций

### Создание нагрузки

Для создания нагрузки и проверки работоспособности можно использовать утилиту **stress-ng**.

https://github.com/ColinIanKing/stress-ng

Пример работы:

```bash
stress-ng --vm 2 --vm-bytes 1G --timeout 1m
```

### Мониторинг стабильности

**vmstat** - virtual memory statistics - утилита для мониторинга стабильности виртуальной памяти, I/O, CPU.

По ней можно понять динамику изменений в функционировании виртуальной памяти.

Пример работы:

```bash
vmstat 1
```

## Сеть

### Метрики

- Пропускная способность

- Задержка

- Процент потерянных пакетов, ошибок

### LTP тесты

К тестам файловой системы можно отнести:

- Всё содержимое testcases/network/

- listen, connect, accept из testcases/kernel/syscalls/

### Тестирование сети

[iperf3](https://github.com/esnet/iperf) - утилита для тестирования сети и её пропускной способности.

Пример работы:

На первом устройстве-сервере

```bash
iperf3 -s -p 8080
```

На втором устройстве-клиенте

```bash
iperf3 -c 127.0.0.1 -p 8080 -t 30 -i 5
```

## Файловые системы

### Метрики

- Пропускная способность

- Скорость чтения и записи

- Процент ошибок

### LTP тесты

К тестам файловой системы можно отнести:

- Всё содержимое testcases/kernel/fs/

- open, close, read, write

- mkdir, chmod, chown

- mount, umount

И другие из testcases/kernel/syscalls/

### Создание нагрузки на файловые системы и диски

[fio](https://github.com/axboe/fio) - flexible I/O tester - утилита для тестирования производительности файловых систем и дисков. Де-факто стандарт для тестирования блочного доступа.

Она позволяет создавать различную нагрузку и измерять основные метрики.

Пример работы:

```bash
fio --name=seq_write --size=2G --rw=write --bs=1M --numjobs=1 --direct=1 --ioengine=libaio --runtime=10s --time_based
```

### Визуализация результатов (fio-plot)

[fio-plot](https://github.com/louwrentius/fio-plot) - утилита, генерирующая графики и диаграммы на основе данных и статистики fio. Работает с форматами json и csv, поддерживается всеми основными ОС.

Информация по установке есть в репозитории по ссылке выше.

#### Пример работы

Сначала сгенерируем 3 json файла:

```bash
fio --name=test1 --ioengine=libaio --direct=1 --size=1G --runtime=30 --filename=/tmp/testfile --rw=randread --bs=4k --iodepth=1 --numjobs=1 --output=results1.json --output-format=json

fio --name=test2 --ioengine=libaio --direct=1 --size=1G --runtime=30 --filename=/tmp/testfile --rw=randread --bs=4k --iodepth=8 --numjobs=1 --output=results2.json --output-format=json

fio --name=test3 --ioengine=libaio --direct=1 --size=1G --runtime=30 --filename=/tmp/testfile --rw=randread --bs=4k --iodepth=16 --numjobs=1 --output=results3.json --output-format=json
```

Для минимального варианта запуска fio-plot необходимо указать следующие аргументы:
* -i - директория с файлами
* -T - заголовок графика
* (-L | -l | -N | -H | -g | -C) - вид графика (линейный, логарифмический, нормализованный, гистограмма, сгруппированный, временной)
* -r - вид операции

Важно отметить, что fio-plot группирует файлы сначала по --iodepth, затем по --numjobs, поэтому эти параметры должны быть указаны и различны у запусков fio, чтобы не было ошибки.

IOPS (Input/Output Operations Per Second) - количество операций в секунду.

Latency - время выполнения одной операции.

**Линейный график**

![Линейный график](https://github.com/user-attachments/assets/5b527be6-f5a0-44c1-87e5-6bd05eb86560)

```bash
fio-plot -i . -T "Linear" -L -t iops -r randread
```

**Логарифмический график**

![Логарифмический график](https://github.com/user-attachments/assets/0f346908-e337-41a8-abb2-b377be3f65e2)

```bash
fio-plot -i . -T "Logarithmic" -l -r randread
```

**Нормализованный график**

![Нормализованный график](https://github.com/user-attachments/assets/593175e4-eb10-427f-ac23-046459ca77e1)

Для запуска нормализованного графика iodepth будет совпадать, но numjobs должен отличаться.

```bash
fio-plot -i . -T "Normalized" -N -r randread
```

**Гистограмма**

![Гистограмма](https://github.com/user-attachments/assets/a20ae52c-04dd-4330-b648-808854cb16b0)

```bash
fio-plot -i . -T "Histogram" -H -r randread
```

### pgbench

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

### SQLIOSim

SQLIOSim - приложение для имитации действий SQL Server на уровне дисковых операций. Его можно использовать для тестирования надежности и целостности дисковых подсистем.

Входит в стандартный набор программ при установке Microsoft SQL Server и связан с ним тем, что он имитирует выполнение его операций. 

SQLIOSim заточен под Windows, но его можно использовать и в Linux (Red Hat, SUSE, Ubuntu).

Для осуществления моделирования операций ввода-вывода через графический интерфейс, необходимо запустить приложение по пути:

```
C:\Program Files\Microsoft SQL Server\MSSQLXX.<InstanceName>\MSSQL\Binn\SQLIOSIM.exe"
```

После [настройки конфигурации]((https://learn.microsoft.com/ru-ru/troubleshoot/sql/tools/sqliosim-utility-simulate-activity-disk-subsystem)) можно начать симуляцию.

Пример вывода из графического интерфейса:

```
 ********** Final Summary for file C:\temp\sqliosim.mdx **********
Target IO Duration (ms) = 100, Running Average IO Duration (ms) = 0, Number of times IO throttled = 89978, IO request blocks = 62
Reads = 200524, Scatter Reads = 336282, Writes = 7631, Gather Writes = 249396, Total IO Time (ms) = 43265879
DRIVE LEVEL: Sector size = 512, Cylinders = 31130, Media type = 12, Sectors per track = 63, Tracks per Cylinders = 255
DRIVE LEVEL: Read cache enabled = Yes, Write cache enabled = Yes
DRIVE LEVEL: Read count = 542111, Read time = 1684781, Write count = 502093, Write time = 42903603, Idle time = 50282, Bytes read = 55905911808, Bytes written = 69013877248, Split IO Count = 1204, Storage number = 3, Storage manager name = VOLMGR

********** Final Summary for file C:\temp\sqliosim.ldx **********
Target IO Duration (ms) = 100, Running Average IO Duration (ms) = 35, Number of times IO throttled = 301, IO request blocks = 9
Reads = 335, Scatter Reads = 0, Writes = 240280, Gather Writes = 0, Total IO Time (ms) = 1336325
DRIVE LEVEL: Sector size = 512, Cylinders = 31130, Media type = 12, Sectors per track = 63, Tracks per Cylinders = 255
DRIVE LEVEL: Read cache enabled = Yes, Write cache enabled = Yes
DRIVE LEVEL: Read count = 542116, Read time = 1684788, Write count = 502101, Write time = 42903604, Idle time = 50447, Bytes read = 55906038784, Bytes written = 69013914112, Split IO Count = 1204, Storage number = 3, Storage manager name = VOLMGR
```

* sqliosim.mdx - файл данных
* sqliosim.ldx - журнал транзакций
* sqliosim.log.xml - журнал ошибок

Возможен запуск через командную строку, для этого нужно указать путь до конфигурации и до места сохранения логов:

```
SQLIOSIM.COM -cfg C:\temp\sqliosim.cfg.ini -log C:\temp\sqliosim.log.xml 
```

Будет сформирован файл с описанием всех событий во время тестирования и результатами. Пример вывода:

```
<ENTRY TYPE='INFO' TIME='02:57:30' DATE='11/08/25' TID='9080' User='Монитор' File='FileIO.cpp' Func='CLogicalFile::OutputSummary' HRESULT='' SYSTEXT=''>
<EXTENDED_DESCRIPTION>DRIVE LEVEL: Read count = 145369, Read time = 112396, Write count = 2698947, Write time = 1797779, Idle time = 2047373, Bytes read = 36437557760, Bytes written = 152289914880, Split IO Count = 857, Storage number = 3, Storage manager name = VOLMGR  </EXTENDED_DESCRIPTION>
</ENTRY>
```

Одновременно можно протестировать несколько томов дисков с помощью -dir, а также указать размеры файлов (МБ) и время выполнения (с):

```
SQLIOSIM.COM -cfg C:\temp\sqliosim.cfg.ini -log C:\temp\sqliosim.log.xml -dir "D:\sqliosim" -dir "F:\sqliosim" -size 500 -d 300
```

### vdbench

[vdbench](https://www.opensourceforu.com/2016/07/vdbench-storage-benchmarking-tool/) - утилита для тестирования I/O дисковых подсистем и создания html отчётов. Работает на различных ОС - Linux, Windows, OS/X.

Запустить vdbench после установки без настройки конфигурации:

```bash
./vdbench -t
```

Результаты будут сохранены в директорию `output`. Описание основных файлов:

* Summary.html – Переходы к другим html файлам и подробный отчёт.
* Totals.html – Итоговая выжимка, без интервальных выводов.
* Logfile.html – Лог всех событий по времени.
* Histogram.html – Распределение времени операций чтения и записи (процентили).
* Flatfile.html – Информация в формате, удобном для создания таблиц и диаграмм.

Пример содержимого Totals.html:

```
15:41:37.002 Starting RD=SD_format; I/O rate: Uncontrolled MAX; elapsed=(none); For loops: threads=2 iorate=max

Nov 08, 2025    interval        i/o   MB/sec   bytes   read     resp     read    write     read    write     resp  queue  cpu%  cpu%
                               rate  1024**2     i/o    pct     time     resp     resp      max      max   stddev  depth sys+u   sys
15:41:38.042     avg_2-1        0.0     0.00       0   0.00    0.000    0.000    0.000     0.00     0.00    0.000    0.0   NaN   NaN

15:41:39.002 Starting RD=rd1; I/O rate: 100; elapsed=5; For loops: None

15:41:44.013     avg_2-5      102.8     0.10    1024  52.31    0.018    0.013    0.024     0.10     0.14    0.017    0.0   0.7   0.1
```

Запустить с конкретной конфигурацией:

```bash
./vdbench -f example -o output
```

Пример конфигурации:

```
sd=sd1,lun=/dev/sda
wd=rr,sd=sd1,xfersize=4096,rdpct=100
rd=run1,wd=rr,iorate=100,elapsed=10,interval=1
```

* SD (storage definition) - дисковое пространство для тестирования.
* WD (workload definition) - параметры нагрузки.
* RD (run definition) - параметры продолжительности.

Существует возможность сравнить результаты различных запусков:

```bash
./vdbench compare output1 output2
```

## Мониторинг утечек

### Метрики

- Потребление памяти

- Соотношение выделенной и освобождённой памяти

### Утилиты для поиска утечек

[valgrind](https://valgrind.org) - популярная утилита для обнаружения утечек и ошибок на уровне пользовательского пространства.

Пример работы:

```bash
valgrind --leak-check=full --show-leak-kinds=all ./test
```

[heaptrack](https://github.com/KDE/heaptrack) - утилита для нахождения утечек в коде.

Предоставляет крайне подробный отчёт об утечках с указанием проблемных мест (есть GUI).

Пример работы:

```bash
heaptrack ./test
heaptrack --analyze "/home/user/heaptrack.test.6202.gz"
```

**kmemleak** - утилита для обнаружения утечек на уровне пространства ядра.

```bash
echo scan > /sys/kernel/debug/kmemleak
cat /sys/kernel/debug/kmemleak
```
