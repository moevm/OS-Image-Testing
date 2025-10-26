# Phoronix Test Suite (PTS)

Phoronix Test Suite — кроссплатформенный фреймворк для автоматизированного бенчмаркинга: сам подтягивает зависимости, ставит тест-профили, запускает прогоны, собирает метрики и формирует отчёты. Результаты легко публиковать и сравнивать через [OpenBenchmarking.org](https://openbenchmarking.org/).

### Типы тестов

Disk — тестирование дисковой подсистемы

Graphics — тестирование графического адаптера (тестируется GPU по умолчанию (может быть как встроенная, так и дискретная))

Memory — тестирование оперативной памяти

Network — тестирование сетевой производительности системы

Processor — тестирование эффективности процессора

System — тестирование общей производительности системы

## Достоинства и недостатки

### Достоинства

- Большая база тестов

- Поддерживается работа из консоли

- Результаты можно сохранять в разных форматах и загружать на сайт

### Недостатки

- Не все тесты поддерживают все ОС — совместимость нужно проверять по каждому профилю

- Есть тесты, которые не запускаются без необходимой лицензии (коммерческие бэнчмарки)

- Сайт openbenchmarking не работает без vpn

- Некоторые тесты требуют долгой загрузки

## Развёртывание (Ubuntu Linux)
```
sudo apt update
sudo apt install -y php-cli php-xml curl git bzip2
sudo apt install -y php-gd
```
`sudo apt install -y php-sqlite3 sqlite3` для поднятия Phoromatic server (опционально)
```
git clone https://github.com/phoronix-test-suite/phoronix-test-suite
cd phoronix-test-suite
sudo ./install-sh
```

## Нахождение тестов и просмотр деталей
```
phoronix-test-suite help
```
Показывает общую справку и список команд

```
phoronix-test-suite list-all-tests
```
Показывает доступные тесты для текущей машины

```
phoronix-test-suite list-recommended-tests
```
Печатает подборку «рекомендуемых» тестов, сгруппированных по категориям

```
phoronix-test-suite info <test>
```
Показывает подробную информацию о тесте

## Запуск тестов
```
phoronix-test-suite benchmark <name>
```
PTS установит тест, зависимости и запустит тестирование

**Настройка и запуск без вопросов**

```
phoronix-test-suite batch-setup
```
Запускает интерактивный опросник и записывает выбранные параметры в ~/.phoronix-test-suite/user-config.xml

```
phoronix-test-suite batch-benchmark <name>
```
Запуск тестов без вопросов (используются параметры из batch-setup)

### Запись датчиков во время тестов
```
MONITOR=all phoronix-test-suite batch-benchmark hmmer
```
Дополнительно пишет частоты, нагрузку, температуру и пр. в файл результата

## Просмотр и экспорт результатов
```
phoronix-test-suite list-results
```
Выводит список сохранённых наборов результатов на этой машине

```
phoronix-test-suite show-result <name>
```
Открывает сохранённый набор результатов с именем <name>

```
phoronix-test-suite result-file-to-<формат> <name>
```
Конвертирует файл результатов в один из форматов: csv, json, pdf, html.

****csv**** - предоставляет данные в удобном виде для построения графиков

****json**** - предоставляет данные в удобном виде для программного парсинга

****html**** - страничка с результатами с сайта OpenBenchmarking

## Интерпретация результатов

В каждом графике указано, что лучше: Higher Is Better или Lower Is Better

Для пропускной способности — «больше лучше»; для времени/латентности — «меньше лучше»

```
phoronix-test-suite result-file-confidence <name>
```
Для каждого теста показывает среднее значение и разброс (стандартное отклонение, процент колебаний) и даёт простой вердикт «стабильно/нестабильно»

```
phoronix-test-suite result-file-stats <name>
```
Делает сводное сравнение, когда в <name> сохранены два или больше прогонов

## Сравнение нескольких результатов
```
phoronix-test-suite merge-results <res1> <res2> [<res3> …]
```
Объединяет несколько файлов результатов в один

```
phoronix-test-suite compare-results-two-way <name>
```
Берёт ровно два прогона из набора <name> и показывает попарное сравнение

## Сравнение на OpenBenchmarking.org
Публикация и открытие результатов
```
phoronix-test-suite upload-result <name>
```
Команда загрузит сохранённый результат <name> и даст ссылку на страницу с графиками

Далее на странице результата можно нажать Compare и добавь ещё один (или несколько)  результатов и получить попарные графики и сводную таблицу «кто быстрее/медленнее» по каждому тесту

## Наиболее часто используемые тесты

### Processor

7-Zip (compress-7zip) — измеряет, сколько «работы по сжатию/распаковке» система делает за секунду

OpenSSL (openssl) — измеряет, сколько мегабайт/сек система хэширует на популярных алгоритмах

FFmpeg (ffmpeg) — измеряет FPS/скорость перекодирования

Build Linux Kernel (build-linux-kernel) — полное время сборки ядра Linux

Build LLVM (build-llvm) — время сборки проекта LLVM/Clang

### Memory

STREAM (pts/stream) — устойчивая пропускная способность памяти (Copy, Scale, Add, Triad)

RAMspeed (pts/ramspeed) — эффективная полоса кэша в режимах INTmem и FLOATmem

Intel MLC (pts/intel-mlc) — латентность (нс) и полоса (GB/s) памяти, в том числе под нагрузкой

MBW (pts/mbw) — скорость копирования в памяти (MEMCPY, DUMB, MCBLOCK)

tinymembench (pts/tinymembench) — пиковая пропускная способность последовательных доступов и латентность случайных доступов

### Disk

FIO (fio) — IOPS, MB/s и задержки для последовательных/случайных чтений/записей и смешанных профилей

FS-Mark (fs-mark) — скорость массового создания/записи/закрытия файлов и fsync (операции/с)

Dbench (dbench) — пропускная способность (MB/s) при воспроизведении реальных файловых вызовов

Tiobench (tiobench) — многопоточный throughput (MB/s) и задержки для последовательного и случайного чтения/записи

### Graphics

DRI_PRIME=1 phoronix-test-suite benchmark <name> — запуск на dGPU

DRI_PRIME=0 phoronix-test-suite benchmark <name> — запуск на iGPU

Unigine Valley (unigine-valley) — средний FPS рендеринга стандартной сцены Unigine

GLmark2 (glmark2) — FPS/балл в наборе OpenGL-тестов

Xonotic (xonotic) — средний FPS в игровом timedemo

Blender (Cycles CPU/GPU) (blender) — время рендеринга кадра в Cycles

### Network

iPerf (iperf) — пропускная способность TCP/UDP между клиентом и сервером (Мбит/с)

Netperf (netperf) — пропускная способность и задержка (latency) для профилей TCP_STREAM/UDP_STREAM и транзакций TCP_RR/UDP_RR

### System

nginx (nginx) — производительность HTTP-сервера (обычно с wrk)

PostgreSQL pgbench (pgbench) — скорость транзакций и латентность при заданном масштабе и параллелизме

PyBench (pybench) — суммарное время выполнения набора микротестов Python

## Примеры

<p align="center">
  <img src="https://github.com/user-attachments/assets/1f005c65-06d0-49d2-b4f7-1389692a307d" width="300" alt="example"><br>
  Рисунок 1 — тест устойчивой пропускной способности оперативной памяти
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/39f81f9a-cbbb-4d5c-85da-49f43240c37b" width="1016" alt="example2"><br>
  Рисунок 2 — пример с сайта openbanchmarking сравнения нескольких результатов
</p>

## Источники

[Официальная документация](https://github.com/phoronix-test-suite/phoronix-test-suite/blob/master/documentation/phoronix-test-suite.md)

[Статья на хабр](https://habr.com/ru/companies/cloud4y/articles/596833/)
