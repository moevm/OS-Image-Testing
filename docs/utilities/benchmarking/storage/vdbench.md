# vdbench

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

Существует возможность сравнить результаты различных запусков (с использованием графического интерфейса):

```bash
./vdbench compare output1 output2
```
