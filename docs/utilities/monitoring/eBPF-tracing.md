## Введение
BPF -- расшифровывается как Berkeley Packet Filter -- технология, состоящая из набора инструкций, вспомогательных типов данных и объектов, функционирующая на уровне ядра операционной системы. Также BPF определяет набор инструкций для виртуальной машины BPF, которые исполняются на уровне ядра, попадая сначала в верификатор, а затем в JIT (Just-in-time) компилятор. Другими словами, BPF -- это виртуальная машина, предоставляющая возможность взаимодействовать с механизмами операционной системы без необходимости подключать новые модули или пересборки OS.

Изначально BPF, разработанный еще в 1992 году, использовался для взаимодействия с сетевыми пакетами. Так, эта технология легла в основу такого сетевого инструмента как tcpdump. Изначальную утилиту принято обозначать как cBPF (где c - classic), а новую расширенную версию eBPF (e -- extended) либо просто BPF.

В последствии механизм BPF многократно расширялся и обновлялся, что превратило BPF в механизм выполнения общего назначения, который можно использовать для самых разных целей, включая создание продвинутых инструментов анализа производительности.

Важно отметить следующее -- BPF -- это набор инструментов для написание программ различного назначения, функционирующих на уровне операционной системы. Написание собственных программ-утилит не является первостепенной задачей текущего проекта. Поэтому сконцентрируемся на обзоре существующих утилит тестирования и анализа производительности на основе eBPF, а имено рассмотрим наборы утилит bcc и bpftrace.

## BCC
BCC (часто пишется просто bcc) -- BPF Compiler Collection, то есть коллекция компиляторов BPF, -- набор инструментов и библиотек для написания BPF программ, в том числе C++ и Python фронт-энды, а также набор готовых утилит для трассировки. Список доступных утилит представлен в виде таблицы:

<table>
  <thead>
    <tr>
      <th>Инструмент</th>
      <th>Область</th>
      <th>Описание</th>
      <th>Пример использования</th>
      <th>Комментарий</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>trace</td>
      <td>Трассировка вызываемых функций</td>
      <td>Трассировка функций с произвольным форматом вывода</td>
      <td><pre># trace 'sys_read (arg3 > 20000) "read %d bytes", arg3'
PID    COMM         FUNC             -
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes</pre>
Здесь мы "отлавливаем" операции чтения большого размера за счет отслеживания системного вызова на чтение, где arg3 -- количество байт на чтение.
</td>
      <td>
      Инструмент очень обширный и может использоваться во множестве ситуаций. Однако требуется вручную придумывать и формулировать сценарии применения.
      Таким образом, trace -- не готовый инструмент оценки производительности, а базовый элемент, из которого потребуется самостоятельно написать необходимую утилиту.
      </td>
    </tr>
    <tr>
      <td>argdist</td>
      <td>Трассировка вызываемых функций</td>
      <td>Трассировка функций на основе передаваемых аргументов в виде гистограмы или подсчета</td>
      <td>Предположим, вам нужна гистограмма размеров буферов, передаваемых в функцию write() по всей системе:
      <pre># argdist -c -H 'p:c:write(int fd, void *buf, size_t len):size_t:len'
[01:45:22]
p:c:write(int fd, void *buf, size_t len):size_t:len
     len                 : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 2        |*************                           |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 2        |*************                           |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 6        |****************************************|
[01:45:23]
p:c:write(int fd, void *buf, size_t len):size_t:len
     len                 : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 11       |***************                         |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 4        |*****                                   |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 28       |****************************************|
        64 -> 127        : 12       |*****************                       |
[01:45:24]
p:c:write(int fd, void *buf, size_t len):size_t:len
     len                 : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 21       |****************                        |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 6        |****                                    |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 52       |****************************************|
        64 -> 127        : 26       |********************                    |
^C</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>funccount</td>
      <td>Трассировка вызываемых функций</td>
      <td>Подсчет частоты вызова функций по маске</td>
      <td><pre># funccount 'vfs_*'
FUNC             COUNT
vfs_statfs         12
vfs_open           121
vfs_getattr        205
vfs_read           492
vfs_write          510
vfs_stat           804</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>stackcount</td>
      <td>Трассировка вызываемых функций</td>
      <td>Частотный анализ стеков вызовов (Stack Trace)</td>
      <td><pre># stackcount submit_bio
  submit_bio
  submit_bh
  ext4_read_block_bitmap_nowait
  ext4_test_allocatable
    3
  submit_bio
  blk_mq_submit_bio
    12</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>execsnoop</td>
      <td>Процессор</td>
      <td>Мониторинг запуска новых процессов (exec)</td>
      <td><pre># execsnoop
PCOMM    PID    PPID   RET ARGS
bash     15887  14902    0 /usr/bin/man ls
preconv  15890  15887    0 /usr/bin/preconv -e UTF-8
man      15894  15887    0 /usr/bin/tbl
ls       15895  15894    0 /bin/ls -F</pre></td>
      <td>
      По аналогии с trace, не дает конкретной информации о производительности системы, однако служит полезным инструментом для более точечной отладки.
      </td>
    </tr>
    <tr>
      <td>runqlat</td>
      <td>Процессор</td>
      <td>Задержка планировщика (как долго процесс ждал CPU)</td>
      <td><pre># runqlat
Tracing run queue latency... Hit Ctrl-C to end.
^C
     usecs               : count     distribution
         0 -> 1          : 233      |***********                             |
         2 -> 3          : 742      |************************************    |
         4 -> 7          : 203      |**********                              |
         8 -> 15         : 173      |********                                |
        16 -> 31         : 24       |*                                       |
        32 -> 63         : 0        |                                        |
        64 -> 127        : 30       |*                                       |
       128 -> 255        : 6        |                                        |
       256 -> 511        : 3        |                                        |
       512 -> 1023       : 5        |                                        |
      1024 -> 2047       : 27       |*                                       |
      2048 -> 4095       : 30       |*                                       |
      4096 -> 8191       : 20       |                                        |
      8192 -> 16383      : 29       |*                                       |
     16384 -> 32767      : 809      |****************************************|
     32768 -> 65535      : 64       |***                                     |</pre></td>
      <td>
      Точечный инструмент оценки производительности процессора. Может быть полезен для мониторинга при попытки оценить производительность конкретной системы в конкретных условиях или для сравнения двух систем в одинаковых условиях.
      </td>
    </tr>
    <tr>
      <td>runqlen</td>
      <td>Процессор</td>
      <td>Длина очереди задач планировщика</td>
      <td><pre># runqlen
Sampling run queue length... Hit Ctrl-C to end.
^C
     runqlen       : count     distribution
        0          : 1068     |****************************************|
        1          : 642      |************************                |
        2          : 369      |*************                           |
        3          : 183      |******                                  |
        4          : 104      |***                                     |
        5          : 42       |*                                       |
        6          : 13       |                                        |
        7          : 2        |                                        |
        8          : 1        |                                        |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>cpudist</td>
      <td>Процессор</td>
      <td>Гистограмма времени, проведенного потоками на CPU</td>
      <td><pre># cpudist.py
Tracing on-CPU time... Hit Ctrl-C to end.
^C
     usecs               : count     distribution
         0 -> 1          : 51       |*                                       |
         2 -> 3          : 395      |***********                             |
         4 -> 7          : 259      |*******                                 |
         8 -> 15         : 61       |*                                       |
        16 -> 31         : 75       |**                                      |
        32 -> 63         : 31       |                                        |
        64 -> 127        : 7        |                                        |
       128 -> 255        : 5        |                                        |
       256 -> 511        : 3        |                                        |
       512 -> 1023       : 5        |                                        |
      1024 -> 2047       : 6        |                                        |
      2048 -> 4095       : 4        |                                        |
      4096 -> 8191       : 1361     |****************************************|
      8192 -> 16383      : 523      |***************                         |
     16384 -> 32767      : 3        |                                        |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>profile</td>
      <td>Процессор</td>
      <td>Профилирование CPU (Sampling) с отображением стеков</td>
      <td><pre># profile
    kthreadd
    ret_from_fork
    -                2
    ...
    sys_clone
    entry_SYSCALL_64
    -                15
    cpuidle_enter_state
    do_idle
    cpu_startup_entry
    -                45</pre></td>
      <td>
        Инструмент полезен для отладки, нежели для оценки производительности.
      </td>
    </tr>
    <tr>
      <td>offcputime</td>
      <td>Процессор</td>
      <td>Анализ времени блокировки процессов (off-CPU)</td>
      <td><pre># offcputime
    finish_task_switch
    schedule
    schedule_timeout
    io_schedule_timeout
    bit_wait_io
    __wait_on_bit
    out_of_line_wait_on_bit
    __ext4_find_entry
    ...
    -                5430</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>syscount</td>
      <td>Процессор</td>
      <td>Топ системных вызовов по количеству или задержке</td>
      <td><pre># syscount
SYSCALL     COUNT
read          452
write         120
futex          98
select         45
epoll_wait     12
openat         10</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>softirq</td>
      <td>Процессор</td>
      <td>Измерение времени обработки программных прерываний (softirq)</td>
      <td><pre># softirqs 10 1
Tracing soft irq event time... Hit Ctrl-C to end.
SOFTIRQ          TOTAL_usecs
net_tx                   633
tasklet                30939
rcu                   143859
sched                 185873
timer                 389144
net_rx               1358268</pre></td>
      <td></td>
    </tr>
    <tr>
      <td>hardirq</td>
      <td>Процессор</td>
      <td>Измерение времени обработки аппаратных прерываний (hardirq)</td>
      <td><pre># hardirqs 10 1
Tracing hard irq event time... Hit Ctrl-C to end.
HARDIRQ                    TOTAL_usecs
ena-mgmnt@pci:0000:00:05.0          43
nvme0q0                             46
eth0-Tx-Rx-7                     47424
eth0-Tx-Rx-6                     48199
eth0-Tx-Rx-5                     48524
eth0-Tx-Rx-2                     49482
eth0-Tx-Rx-3                     49750
eth0-Tx-Rx-0                     51084
eth0-Tx-Rx-4                     51106
eth0-Tx-Rx-1                     52649</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>memleak</td>
      <td>Память</td>
      <td>Поиск утечек памяти (неосвобожденных аллокаций)</td>
      <td><pre># memleak -p 1234
[11:22:33] Top 5 stacks with leaks:
    1024 bytes in 2 allocations from stack
        malloc+0x2e [libc]
        my_leaky_func+0x2f [test_app]
        main+0x4a [test_app]
    512 bytes in 1 allocations from stack
        calloc+0x3d [libc]
        init_buffer+0x1b [test_app]</pre></td>
      <td>
        По аналогии с profile, иструмент полезен для отладки пользовательских программ, нежели для оценки производительности.
      </td>
    </tr>
    <tr>
      <td>opensnoop</td>
      <td>Файловая система</td>
      <td>Трассировка системных вызовов open()</td>
      <td><pre># opensnoop
PID    COMM    FD ERR PATH
2555   git      3   0 .gitignore
2555   git      3   0 .git/HEAD
2560   cat      3   0 /etc/ld.so.cache
2560   cat      3   0 /lib64/libc.so.6
1902   node     4   0 /app/package.json</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>filelife</td>
      <td>Файловая система</td>
      <td>Отслеживание короткоживущих файлов</td>
      <td><pre># filelife
TIME     COMM     PID    AGE(s)  FILE
10:11:02 rm       4111   0.02    temp_1.dat
10:11:05 gcc      5122   0.15    ccXy12.o
10:11:07 cleanup  101    0.05    session.tmp</pre></td>
      <td>
        Может быть полезно для оценки действий пользователя и их влияние на производительности системы в целом.
      </td>
    </tr>
    <tr>
      <td>vfsstat</td>
      <td>Файловая система</td>
      <td>Статистика операций VFS (Virtual File System)</td>
      <td><pre># vfsstat
TIME         READ   WRITE  CREATE    OPEN  FSYNC
18:32:00      121      45       2      12      0
18:32:01       95      20       0       8      1
18:32:02      450     112       5      35      4
18:32:03       20       1       0       1      0</pre></td>
      <td>
        -
      </td>
    </tr>
        <tr>
      <td>fileslower</td>
      <td>Файловая система</td>
      <td>Трассировка медленных операций чтения/записи</td>
      <td><pre># fileslower 10
Tracing...
TIME     COMM   PID D BYTES   LAT(ms) FILENAME
12:10:44 mysqld 192 R 128KB     12.54 data.ibd
12:10:48 java   332 W 4KB       45.11 app.log
12:10:55 sync   551 S 0          9.22 (sync)</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>cachestat</td>
      <td>Файловая система</td>
      <td>Статистика попаданий/промахов в Page Cache</td>
      <td><pre># cachestat
   HITS   MISSES  DIRTIES HITRATIO
   1024        5        2   99.51%
    900       12        0   98.68%
    150      150       10   50.00%
   5000        0        5  100.00%</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>writeback</td>
      <td>Файловая система</td>
      <td>Отслеживание событий записи данных из кэша на диск</td>
      <td><pre># writeback
TIME     DEVICE  PAGES  REASON
12:12:01 sda1      128  background
12:12:02 sda1       64  sync
12:12:05 sda1     1024  periodic</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>dcstat</td>
      <td>Файловая система</td>
      <td>Статистика кэша записей каталогов (dentry cache)</td>
      <td><pre># dcstat
TIME         REFS   SLOW   MISS  HIT%
12:14:01    12540    120     45  99.64%
12:14:02     4500     10      2  99.95%
12:14:03    21000    500    120  99.42%</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>xfsslower</td>
      <td>Файловая система</td>
      <td>Медленные операции в файловой системе XFS</td>
      <td><pre># xfsslower 1
TIME     COMM           PID    T BYTES   OFF_KB   LAT(ms) FILENAME
14:15:22 fsync-tester   3122   S 0       0           2.33 test.bin
14:15:25 db-writer      112    W 4096    12005       1.45 db.dat</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>xfsdist</td>
      <td>Файловая система</td>
      <td>Гистограмма задержек операций XFS</td>
      <td><pre># xfsdist
Tracing XFS operation latency... Hit Ctrl-C to end.
^C
operation = 'read'
     usecs               : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 362      |                                        |
         4 -> 7          : 807      |*                                       |
         8 -> 15         : 20686    |****************************************|
        16 -> 31         : 512      |                                        |
        32 -> 63         : 4        |                                        |
        64 -> 127        : 2744     |*****                                   |
       128 -> 255        : 7127     |*************                           |
       256 -> 511        : 2483     |****                                    |
       512 -> 1023       : 1281     |**                                      |
      1024 -> 2047       : 39       |                                        |
      2048 -> 4095       : 5        |                                        |
      4096 -> 8191       : 1        |                                        |
operation = 'open'
     usecs               : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 3        |****************************************|</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>ext4dist</td>
      <td>Файловая система</td>
      <td>Гистограмма задержек операций ext4</td>
      <td><pre># ext4dist
Tracing ext4 operation latency... Hit Ctrl-C to end.
^C
operation = 'read'
     usecs               : count     distribution
         0 -> 1          : 1210     |****************************************|
         2 -> 3          : 126      |****                                    |
         4 -> 7          : 376      |************                            |
         8 -> 15         : 86       |**                                      |
        16 -> 31         : 9        |                                        |
        32 -> 63         : 47       |*                                       |
        64 -> 127        : 6        |                                        |
       128 -> 255        : 24       |                                        |
       256 -> 511        : 137      |****                                    |
       512 -> 1023       : 66       |**                                      |
      1024 -> 2047       : 13       |                                        |
      2048 -> 4095       : 7        |                                        |
      4096 -> 8191       : 13       |                                        |
      8192 -> 16383      : 3        |                                        |
operation = 'write'
     usecs               : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 75       |****************************************|
        16 -> 31         : 5        |**                                      |
operation = 'open'
     usecs               : count     distribution
         0 -> 1          : 1278     |****************************************|
         2 -> 3          : 40       |*                                       |
         4 -> 7          : 4        |                                        |
         8 -> 15         : 1        |                                        |
        16 -> 31         : 1        |                                        |
</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>biolatency</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма задержек блочного устройства</td>
      <td><pre># biolatency
Tracing block device I/O... Hit Ctrl-C to end.
^C
     usecs           : count     distribution
       0 -> 1        : 0        |                                      |
       2 -> 3        : 0        |                                      |
       4 -> 7        : 0        |                                      |
       8 -> 15       : 0        |                                      |
      16 -> 31       : 0        |                                      |
      32 -> 63       : 0        |                                      |
      64 -> 127      : 1        |                                      |
     128 -> 255      : 12       |********                              |
     256 -> 511      : 15       |**********                            |
     512 -> 1023     : 43       |*******************************       |
    1024 -> 2047     : 52       |**************************************|
    2048 -> 4095     : 47       |**********************************    |
    4096 -> 8191     : 52       |**************************************|
    8192 -> 16383    : 36       |**************************            |
   16384 -> 32767    : 15       |**********                            |
   32768 -> 65535    : 2        |*                                     |
   65536 -> 131071   : 2        |*                                     |</pre></td>
      <td>
        Полезно для трассировки и изучения работы конкретных устройств ввода/вывода.
      </td>
    </tr>
    <tr>
      <td>biosnoop</td>
      <td>Ввод/вывод</td>
      <td>Лог каждой операции ввода-вывода</td>
      <td><pre># biosnoop
TIME     COMM   PID    DISK    T  LAT(ms)
0.000000 super  1921   xvda1   R     0.23
0.000410 jbd2   312    xvda1   W     1.41
0.000550 kwork  15     xvda1   W     0.95
0.001200 db     101    xvdb1   R    12.50</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>biotop</td>
      <td>Ввод/вывод</td>
      <td>Топ процессов по использованию диска</td>
      <td><pre># biotop
PID    COMM     R/W   MAJ:MIN   BYTES   AVG_MS
1234   dd         W   202:1     102400    1.2
4321   cksum      R   202:1      40960    0.8
112    mysqld     R   202:1       8192    5.5</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>bitesize</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма размеров I/O операций по процессам</td>
      <td><pre># ./bitesize
Tracing... Hit Ctrl-C to end.
^C
Process Name = 'kworker/u128:1'
     Kbytes              : count     distribution
         0 -> 1          : 1        |********************                    |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 2        |****************************************|
Process Name = 'bitesize'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 0        |                                        |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 0        |                                        |
        64 -> 127        : 0        |                                        |
       128 -> 255        : 1        |****************************************|
Process Name = 'dd'
     Kbytes              : count     distribution
         0 -> 1          : 3        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 6        |                                        |
         8 -> 15         : 0        |                                        |
        16 -> 31         : 1        |                                        |
        32 -> 63         : 1        |                                        |
        64 -> 127        : 0        |                                        |
       128 -> 255        : 0        |                                        |
       256 -> 511        : 1        |                                        |
       512 -> 1023       : 0        |                                        |
      1024 -> 2047       : 488      |****************************************|
Process Name = 'jbd2/dm-1-8'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 1        |****************************************|
Process Name = 'cat'
     Kbytes              : count     distribution
         0 -> 1          : 1        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 0        |                                        |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 1        |                                        |
        64 -> 127        : 0        |                                        |
       128 -> 255        : 0        |                                        |
       256 -> 511        : 1924     |****************************************|
Process Name = 'ntpd'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 104      |****************************************|
Process Name = 'vmtoolsd'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 1        |****************************************|
Process Name = 'bash'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 0        |                                        |
         8 -> 15         : 0        |                                        |
        16 -> 31         : 2        |****************************************|
Process Name = 'jbd2/sdb-8'
     Kbytes              : count     distribution
         0 -> 1          : 0        |                                        |
         2 -> 3          : 0        |                                        |
         4 -> 7          : 1        |****************************************|
         8 -> 15         : 0        |                                        |
        16 -> 31         : 0        |                                        |
        32 -> 63         : 1        |****************************************|</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpconnect</td>
      <td>Сети</td>
      <td>Лог новых исходящих соединений</td>
      <td><pre># tcpconnect
PID    COMM      IP SADDR       DADDR       DPORT
1421   curl      4  10.0.0.1    8.8.8.8     80
3112   wget      4  10.0.0.1    1.1.1.1     443
4005   node      6  fe80::1     fe80::2     3000</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpaccept</td>
      <td>Сети</td>
      <td>Лог входящих соединений</td>
      <td><pre># tcpaccept
PID    COMM     IP RADDR        LADDR       LPORT
22     sshd     4  192.168.1.5  192.168.1.1 22
80     nginx    4  10.5.5.1     10.0.0.2    80</pre></td>
      <td>
        В большей степени полезен для мониторинга действий пользователя, нежели для оценки производительности системы.
      </td>
    </tr>
    <tr>
      <td>tcplife</td>
      <td>Сети</td>
      <td>Продолжительность TCP сессий</td>
      <td><pre># tcplife
PID   COMM  LPORT RPORT TX_KB RX_KB MS
221   ssh    22   4312    24    2   1500
411   curl   5432 80       1   50     45
501   bg     443  31210  100    0    500</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpretrans</td>
      <td>Сети</td>
      <td>Повторные отправки пакетов (ретрасмиты)</td>
      <td><pre># tcpretrans
TIME     PID    LADDR:LPORT  --&gt; RADDR:RPORT
10:21:22 121    10.0.2.15:22 --&gt; 192.168.1.5:41
10:21:25 121    10.0.2.15:22 --&gt; 192.168.1.5:41</pre></td>
      <td>
        Полезно для мониторинга конкретных сценариев использования, нежели для оценки производительности как таковой.
      </td>
    </tr>
    <tr>
      <td>capable</td>
      <td>Безопасность</td>
      <td>Проверки security capabilities ядра</td>
      <td><pre># capable
TIME     UID  PID  COMM     CAP  NAME         AUDIT
10:11:12 0    123  chown    0    CAP_CHOWN    1
10:11:15 1000 455  ping     13   CAP_NET_RAW  1
10:11:20 0    501  insmod   21   CAP_SYS_MODULE 1</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>javastat</td>
      <td>Языка</td>
      <td>Общая статистика по JVM (GC, аллокации, нагрузка)</td>
      <td><pre># javastat 1234
TIME      LOAD    GC_MS  ALLOC_MB
10:30:00  0.5     12     500
10:30:01  0.6     0      120
10:30:02  0.8     155    800
10:30:03  0.4     0      50</pre></td>
      <td>
        Полезен в пользовательскиз сценариях использования (в которых используется язык Java)
      </td>
    </tr>
    <tr>
      <td>javacalls</td>
      <td>Языка</td>
      <td>Трассировка вызовов Java-методов</td>
      <td><pre># javacalls 1234
METHOD                            CALLS
java/io/File.exists                 152
java/lang/String.length              54
org/apache/catalina/Server.start      1</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>javathreads</td>
      <td>Языка</td>
      <td>Трассировка переключений потоков Java</td>
      <td><pre># javathreads 1234
TIME      THREAD         STATE
10:30:01  main           RUNNABLE
10:30:01  Worker-1       BLOCKED
10:30:01  GC-Thread      RUNNABLE</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>javaflow</td>
      <td>Языка</td>
      <td>Визуализация потока выполнения методов Java</td>
      <td><pre># javaflow 1234
CPU PID    TID    TIME(us) METHOD
1   1234   1240   150      <- java/io/InputStream.read
1   1234   1240   12       -> java/lang/String.equals
1   1234   1240   13       <- java/lang/String.equals</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>javagc</td>
      <td>Языка</td>
      <td>Лог событий сборки мусора Java</td>
      <td><pre># javagc 1234
TIME      GC_MS  TYPE
10:30:05  15     Young Gen
10:30:10  120    Full GC
10:30:25  22     Young Gen</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>mysqld_qslower</td>
      <td>Приложения</td>
      <td>Медленные запросы MySQL</td>
      <td><pre># mysqld_qslower `pgrep -n mysqld` 1
TIME     PID    MS    QUERY
10:11:12 321    1500  SELECT * FROM users JOIN ...
10:11:15 321    2100  UPDATE sessions SET ...</pre></td>
      <td>
        Полезен в пользовательских сценариях (если используется SQL)
      </td>
    </tr>
    <tr>
      <td>signals</td>
      <td>Приложения</td>
      <td>Отслеживание отправки сигналов (kill, tgkill)</td>
      <td><pre># signals
TIME     PID    COMM   TPID   SIG  RET
12:15:01 123    bash   456    9    0
12:15:10 881    pkill  1021   15   0
12:15:20 1      systemd 501   15   0</pre></td>
      <td>
        Полезно для отладки при конкретном сценарии использования системы.
      </td>
    </tr>
    <tr>
      <td>killsnoop</td>
      <td>Приложения</td>
      <td>Отслеживание сигналов через kill()</td>
      <td><pre># killsnoop
TIME     PID    COMM   SIG  TPID  RESULT
12:12:12 512    bash   9    1200  0
12:12:15 512    bash   2    1200  0
12:12:20 800    top    15   950   -1</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>wakeuptime</td>
      <td>Ядро</td>
      <td>Анализ стеков, пробуждающих процесс</td>
      <td><pre># wakeuptime
    target:          sshd
    try_to_wake_up
    autoremove_wake_function
    __wake_up_common
    __wake_up_common_lock
    __wake_up_sync_key
    sock_def_readable
    ...
    -                543</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>offwaketime</td>
      <td>Ядро</td>
      <td>Отображает трассировки стека ядра и имена задач, которые были заблокированы и находились вне CPU ("off-CPU"), а также трассировки стека и имена задач для потоков, которые их разбудили, и общее время, прошедшее с момента блокировки до момента пробуждения.</td>
      <td><pre># offwaketime 5
Tracing blocked time (us) by kernel off-CPU and waker stack for 5 secs.
[...]
    waker:           swapper/0
    ffffffff8137897c blk_mq_complete_request
    ffffffff81378930 __blk_mq_complete_request
    ffffffff81378793 blk_mq_end_request
    ffffffff813778b9 blk_mq_free_request
    ffffffff8137782d __blk_mq_free_request
    ffffffff8137bc57 blk_mq_put_tag
    ffffffff8137b2c7 bt_clear_tag
    ffffffff810b54d9 __wake_up
    ffffffff810b5462 __wake_up_common
    ffffffff810b5b12 autoremove_wake_function
    -                -
    ffffffff81785085 schedule
    ffffffff81787e16 schedule_timeout
    ffffffff81784634 __sched_text_start
    ffffffff8137b839 bt_get
    ffffffff8137bbf7 blk_mq_get_tag
    ffffffff8137761b __blk_mq_alloc_request
    ffffffff81379442 blk_mq_map_request
    ffffffff8137a445 blk_sq_make_request
    ffffffff8136ebc3 generic_make_request
    ffffffff8136ed07 submit_bio
    ffffffff81225adf submit_bh_wbc
    ffffffff81225b42 submit_bh
    ffffffff812721e0 __ext4_get_inode_loc
    ffffffff812751dd ext4_iget
    ffffffff81275c90 ext4_iget_normal
    ffffffff8127f45b ext4_lookup
    ffffffff811f94ed lookup_real
    ffffffff811fad43 __lookup_hash
    ffffffff811fc3fb walk_component
    ffffffff811fd050 link_path_walk
    target:          cksum
        56529
[...]
Detaching...
</pre></td>
      <td>
        -
      </td>
    </tr>
  </tbody>
</table>

## bpftrace
bpftrace -- это трассировщик с открытым исходным кодом, основанный на BPF и BCC. Проект bpftrace, так же как BCC, включает множество инструментов оценки производительности с сопроводительной документацией. Он также предоставляет язык программирования высокого уровня, позволяющий писать мощные инструменты. Написание и запуск подобных программ требует наличия root привелегий, которые нужны для загрузки BPF-программ в ядро. Сами программы функционируют на уровне системы, то есть отслеживают действия всех пользователей. Однако bpftrace предоставляет возмоность фильтрации по пользователям за счет парметров uid, gid и username. Так, например можно осуществить трассировку вызовов, исключая действия root-а:
```
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_execve /uid != 0/ { printf("User %d ran: %s\n", uid, str(args->filename)); }'
```
Однако подобные условия и фильтры придется реализовывать вручную.

Ниже представлена таблица готовых инструментов bpftrace:

<table>
  <thead>
    <tr>
      <th>Инструмент</th>
      <th>Область</th>
      <th>Описание</th>
      <th>Пример использования</th>
      <th>Комментарий</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>execsnoop.bt</td>
      <td>Трассировка вызываемых функций</td>
      <td>Отслеживание запуска новых процессов и аргументов командной строки.</td>
      <td><pre># execsnoop.bt
TIME     PID    PPID   COMM     ARGS
10:43:10 24106  24100  bash     /usr/bin/man ls
10:43:10 24112  24106  preconv  /usr/bin/preconv -e UTF-8
10:43:10 24115  24106  man      /usr/bin/tbl
10:43:10 24116  24115  ls       /bin/ls -F</pre></td>
      <td>
        Полезно для супервайзинга действий пользователя. К тестированию производиельности системы вряд ли относится.
      </td>
    </tr>
    <tr>
      <td>threadsnoop.bt</td>
      <td>Трассировка вызываемых функций</td>
      <td>Отслеживание создания новых потоков (threads).</td>
      <td><pre># threadsnoop.bt
TIME     PID    COMM         FUNC
01:32:05 15432  java         pthread_create
01:32:05 2021   gnome-shell  pthread_create
01:32:06 100    systemd      clone</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>opensnoop.bt</td>
      <td>Трассировка вызываемых функций</td>
      <td>Трассировка системного вызова open() с именами файлов.</td>
      <td><pre># opensnoop.bt
TIME     PID    COMM       FD ERR PATH
04:22:10 1421   nginx       6   0 /etc/nginx/nginx.conf
04:22:10 1421   nginx       7   0 /var/log/nginx/access.log
04:22:15 892    cat         3   0 /proc/cpuinfo</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>killsnoop.bt</td>
      <td>Трассировка вызываемых функций</td>
      <td>Отслеживание сигналов, отправленных через kill().</td>
      <td><pre># killsnoop.bt
TIME     PID    COMM     SIG  TPID   RESULT
08:12:00 5122   bash     9    1200   0
08:12:05 5122   bash     15   1200   0
08:12:10 999    systemd  9    150    -1</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>signals.bt</td>
      <td>Трассировка вызываемых функций</td>
      <td>Подсчет количества отправленных сигналов в виде стековой диаграммы</td>
      <td><pre># signals.bt
Attaching 2 probes...
@:[SIGHUP]: 1
@:[SIGKILL]: 12
@:[SIGTERM]: 45
@:[SIGINT]: 102</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>runqlat.bt</td>
      <td>Процессор</td>
      <td>Гистограмма задержек планировщика (время ожидания CPU).</td>
      <td><pre># runqlat.bt
@usecs:
[0]                    1 |                                                    |
[1]                   11 |@@                                                  |
[2, 4)                16 |@@@                                                 |
[4, 8)                43 |@@@@@@@@@@                                          |
[8, 16)              134 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                     |
[16, 32)             220 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[32, 64)             117 |@@@@@@@@@@@@@@@@@@@@@@@@@@@                         |
[64, 128)             84 |@@@@@@@@@@@@@@@@@@@                                 |
[128, 256)            10 |@@                                                  |
[256, 512)             2 |                                                    |
[512, 1K)              5 |@                                                   |
[1K, 2K)               5 |@                                                   |
[2K, 4K)               5 |@                                                   |
[4K, 8K)               4 |                                                    |
[8K, 16K)              1 |                                                    |
[16K, 32K)             2 |                                                    |
[32K, 64K)             0 |                                                    |
[64K, 128K)            1 |                                                    |
[128K, 256K)           0 |                                                    |
[256K, 512K)           0 |                                                    |
[512K, 1M)             1 |                                                    |
</pre></td>
      <td>
        Может использоваться как вспомогательный интсрумент мониторинга при исследовании работы системы с различными задачами и различной нагрузкой.
      </td>
    </tr>
    <tr>
      <td>runqlen.bt</td>
      <td>Процессор</td>
      <td>Гистограмма длины очереди задач планировщика (нагрузка на CPU).</td>
      <td><pre># runqlen.bt
Attaching 2 probes...
Sampling run queue length at 99 Hertz... Hit Ctrl-C to end.
^C
@runqlen:
[0, 1)              1967 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[1, 2)                 0 |                                                    |
[2, 3)                 0 |                                                    |
[3, 4)               306 |@@@@@@@@                                            |pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>cpuwalk.bt</td>
      <td>Процессор</td>
      <td>Профилирование CPU: какие функции выполняются (Sampling).</td>
      <td><pre># cpuwalk.bt
Attaching 49 probes...
@:
    entry_SYSCALL_64_after_hwframe
    do_syscall_64
    sys_read
    vfs_read
    ...
    521</pre></td>
      <td>
        Полезно для отладки.
      </td>
    </tr>
    <tr>
      <td>offcputime.bt</td>
      <td>Процессор</td>
      <td>Стеки вызовов, когда процесс блокируется (уходит с CPU).</td>
      <td><pre># offcputime.bt
    finish_task_switch
    __schedule
    schedule
    pipe_wait
    pipe_read
    ...
    1250</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>oomkill.bt</td>
      <td>Память</td>
      <td>Отслеживание срабатывания OOM Killer (Out of Memory).</td>
      <td><pre># oomkill.bt
TIME     TRIGGERED_BY  PID   KILLED_COMM  KILLED_PID PAGES
12:00:01 java          5100  postgres     4200       150222
12:30:05 stress        8100  stress       8100       50000</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>faults.bt</td>
      <td>Память</td>
      <td>Подсчет страничных ошибок (page faults) по процессам.</td>
      <td><pre># faults.bt
TIME     COMM     PID    TYPE     ADDR
10:10:05 node     1234   minor    0x7f...
10:10:06 java     5678   major    0x55...
10:10:06 cc1      9911   minor    0x7f...</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>vmscan.bt</td>
      <td>Память</td>
      <td>Анализ работы алгоритма возврата страниц (page reclaim).</td>
      <td><pre># vmscan.bt
TIME     PID    COMM         ANON  FILE  RECLAIMED
14:15:00 100    kswapd0      1200  500   1700
14:15:05 5200   chrome       50    10    60</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>swapin.bt</td>
      <td>Память</td>
      <td>Отслеживание подкачки страниц из swap (swapin).</td>
      <td><pre># swapin.bt
TIME     PID    COMM         COUNT
15:00:01 1234   java         512
15:00:05 4321   mysqld       128</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>vfsstat.bt</td>
      <td>Файловая система</td>
      <td>Статистика операций VFS (read, write, open и т.д.).</td>
      <td><pre># vfsstat.bt
TIME       READ   WRITE  CREATE  OPEN   FSYNC
10:00:01   400    120    5       50     2
10:00:02   350    10     0       12     0
10:00:03   1200   500    20      100    10</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>filelife.bt</td>
      <td>Файловая система</td>
      <td>Отслеживание времени жизни короткоживущих файлов.</td>
      <td><pre># filelife.bt
TIME     PID    COMM     AGE(ms)  FILE
09:15:10 1200   rm       12       /tmp/x86.tmp
09:15:12 1250   gcc      55       /tmp/ccXy.o</pre></td>
      <td>
        Полезно для трассировки действий пользователя. Не подходит для общей оценки производительности.
      </td>
    </tr>
    <tr>
      <td>xfsdist.bt</td>
      <td>Файловая система</td>
      <td>Гистограмма задержек операций XFS.</td>
      <td><pre># xfsdist.bt
@usecs[read]:
[0, 255]              52 |@@@@@@@@@@@@@@@@@@@@@@              |
[256, 1023]           12 |@@@@@                               |
[1024, 4095]           2 |@                                   |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>biosnoop.bt</td>
      <td>Ввод/вывод</td>
      <td>Трассировка блочного ввода-вывода с задержками.</td>
      <td><pre># biosnoop.bt
TIME     COMM      PID    DISK    T  SECTOR     BYTES  LAT(ms)
01:00:00 jbd2/sda1 312    sda1    W  2412234    4096   0.55
01:00:01 dd        5100   sdb     R  1024       8192   12.01</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>biolatency.bt</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма задержек блочного устройства.</td>
      <td><pre># biolatency.bt
@usecs:
[256, 511]           421 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@      |
[512, 1023]          120 |@@@@@@                              |
[1024, 2047]          50 |@@@                                 |
[2048, 4095]           5 |                                    |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>bitesize.bt</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма размеров I/O запросов по процессам.</td>
      <td><pre># bitesize.bt
@bytes[dd]:
[4k, 8k)             100 |@@@@@@@@@@@@@@@@@                   |
[8k, 16k)            250 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[16k, 32k)            10 |@                                   |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>biostacks.bt</td>
      <td>Ввод/вывод</td>
      <td>Показывает стек ядра, инициировавший дисковый I/O.</td>
      <td><pre># biostacks.bt
@stacks:
    blk_mq_submit_bio
    submit_bio_noacct
    ext4_read_block_bitmap_nowait
    ...
    12</pre></td>
      <td>
        Полезно для отладки.
      </td>
    </tr>
    <tr>
      <td>scsilatency.bt</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма задержек команд SCSI.</td>
      <td><pre># scsilatency.bt
@usecs:
[0, 1000]            500 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[1000, 2000]          20 |@@                                  |
[2000, 4000]           5 |                                    |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>nvmelatency.bt</td>
      <td>Ввод/вывод</td>
      <td>Гистограмма задержек команд NVMe.</td>
      <td><pre># nvmelatency.bt
@usecs:
[0, 64]             1200 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[64, 128]             50 |@@                                  |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpconnect.bt</td>
      <td>Сети</td>
      <td>Лог новых исходящих TCP-соединений.</td>
      <td><pre># tcpconnect.bt
TIME     PID    COMM     SADDR          DADDR          DPORT
12:12:01 1422   curl     192.168.1.5    8.8.8.8        80
12:12:05 5122   ssh      192.168.1.5    10.0.0.2       22</pre></td>
      <td>
        Полезно для супервайзинга, не относится к оценке производительности системы.
      </td>
    </tr>
    <tr>
      <td>tcpaccept.bt</td>
      <td>Сети</td>
      <td>Лог новых входящих TCP-соединений.</td>
      <td><pre># tcpaccept.bt
TIME     PID    COMM     SADDR          DADDR          LPORT
12:15:00 421    sshd     10.5.5.1       192.168.1.5    22
12:15:05 80     nginx    123.45.67.89   192.168.1.5    443</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpdrop.bt</td>
      <td>Сети</td>
      <td>Отслеживание сброшенных ядром пакетов (drop).</td>
      <td><pre># tcpdrop.bt
TIME     PID    COMM     SADDR:SPORT       DADDR:DPORT   STATE
12:20:01 0      swapper  10.0.0.1:45122    10.0.0.2:80   ESTABLISHED
12:20:05 0      swapper  192.168.1.5:22    1.2.3.4:5512  CLOSE_WAIT</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>tcpretrans.bt</td>
      <td>Сети</td>
      <td>Подсчет повторных передач (retransmits) TCP.</td>
      <td><pre># tcpretrans.bt
TIME     PID    COMM     LADDR:LPORT       RADDR:RPORT   STATE
12:25:01 1200   wget     10.0.0.5:41222    8.8.8.8:80    ESTABLISHED</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>gethostlatency.bt</td>
      <td>Сети</td>
      <td>Задержка разрешения имен DNS (getaddrinfo/gethostbyname).</td>
      <td><pre># gethostlatency.bt
TIME     PID    COMM     LATms HOST
12:30:00 1421   ping     5.12  google.com
12:30:05 3122   curl     120.5 example.local</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>ttysnoop.bt</td>
      <td>Безопасность</td>
      <td>Перехват вывода на терминал (TTY) другого пользователя.</td>
      <td><pre># ttysnoop.bt /dev/pts/1
TIME     PID    COMM     FUNC             LEN
14:00:01 2511   bash     tty_write        5
&lt;User types: ls -la&gt;</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>elfsnoop.bt</td>
      <td>Безопасность</td>
      <td>Отслеживание запуска исполняемых файлов ELF.</td>
      <td><pre># elfsnoop.bt
TIME     PID    COMM     PATH
14:05:00 5122   bash     /bin/ls
14:05:01 5123   ls       /lib64/ld-linux-x86-64.so.2</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>setuids.bt</td>
      <td>Безопасность</td>
      <td>Отслеживание вызовов setuid (повышение привилегий).</td>
      <td><pre># setuids.bt
TIME     PID    COMM     UID    GID    EUID   EGID
14:10:00 1200   sudo     1000   1000   0      0
14:10:05 1201   su       1000   1000   0      0</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>jnistacks.bt</td>
      <td>Языки (Java)</td>
      <td>Стеки вызовов при переходе Java -> Native (JNI).</td>
      <td><pre># jnistacks.bt
@stacks:
    Java_java_io_UnixFileSystem_getBooleanAttributes0
    java.io.UnixFileSystem.getBooleanAttributes0
    java.io.File.exists
    ...
    12</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>javacalls.bt</td>
      <td>Языки (Java)</td>
      <td>Подсчет количества вызовов методов Java.</td>
      <td><pre># javacalls.bt
Attaching...
@calls[java/lang/Math.random]: 150
@calls[java/io/File.exists]: 42
@calls[org/apache/catalina/core/StandardWrapper.service]: 10</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>pmheld.bt</td>
      <td>Приложения</td>
      <td>Время удержания мьютексов pthread (mutex held time).</td>
      <td><pre># pmheld.bt
@held_usecs:
[0, 1]                50 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[2, 3]                10 |@@@@                                |
[4, 7]                 1 |                                    |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>naptime.bt</td>
      <td>Приложения</td>
      <td>Анализ времени сна процессов (nanosleep, usleep).</td>
      <td><pre># naptime.bt
TIME     PID    COMM     SEC    NSEC
15:00:00 1200   sleep    1      0
15:00:05 5122   node     0      500000000</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>mysqld_qslower.bt</td>
      <td>Приложения</td>
      <td>Медленные запросы MySQL (анализ текста запроса).</td>
      <td><pre># mysqld_qslower.bt 5
TIME     PID    MS    QUERY
15:10:00 2411   1500  SELECT * FROM big_table JOIN ...
15:10:05 2412   6000  ALTER TABLE logs ADD COLUMN ...</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>mlock.bt</td>
      <td>Ядро</td>
      <td>Отслеживание блокировок мьютексов ядра.</td>
      <td><pre># mlock.bt
@locks:
    [0xffffffff81a03040]    120
    [0xffffffff81a03080]    45</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>mheld.bt</td>
      <td>Ядро</td>
      <td>Время удержания мьютексов ядра.</td>
      <td><pre># mheld.bt
@held_usecs:
[0, 1]               400 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[2, 3]                20 |@                                   |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>kmem.bt</td>
      <td>Ядро</td>
      <td>Отслеживание аллокаций памяти ядра (kmalloc/kfree).</td>
      <td><pre># kmem.bt
@bytes_alloc[kmalloc-256]: 40960
@bytes_alloc[kmalloc-512]: 102400</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>kpages.bt</td>
      <td>Ядро</td>
      <td>Статистика работы со страницами ядра (allocation/free).</td>
      <td><pre># kpages.bt
TIME     PID    COMM     FUNC             PAGES
15:30:00 100    kswapd   __alloc_pages    1
15:30:00 100    kswapd   free_hot_cold    1</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>workq.bt</td>
      <td>Ядро</td>
      <td>Задержки выполнения в очередях задач ядра (workqueues).</td>
      <td><pre># workq.bt
@usecs[events]:
[0, 1]               500 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[2, 3]                12 |                                    |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>pidnss.bt</td>
      <td>Контейнеры</td>
      <td>Отслеживание создания новых PID пространств имен.</td>
      <td><pre># pidnss.bt
TIME     PID    COMM     NS_INO
16:00:00 5122   dockerd  4026531836
16:00:05 5150   runc     4026532100</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>blkthrot.bt</td>
      <td>Контейнеры</td>
      <td>Отслеживание троттлинга блочного устройства (cgroups).</td>
      <td><pre># blkthrot.bt
TIME     PID    COMM     LAT(ms)
16:10:00 1200   dd       15.2
16:10:05 1200   dd       25.4</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>xenhyper.bt</td>
      <td>Гипервизоры</td>
      <td>Подсчет количества гипервызовов Xen (hypercalls).</td>
      <td><pre># xenhyper.bt
@hypercalls[HYPERVISOR_sched_op]: 1500
@hypercalls[HYPERVISOR_memory_op]: 400</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>cpustolen.bt</td>
      <td>Гипервизоры</td>
      <td>Анализ "украденного" времени CPU (stolen time) в виртуалках.</td>
      <td><pre># cpustolen.bt
@stolen_usecs:
[0, 255]             500 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[256, 1023]           50 |@@@@                                |</pre></td>
      <td>
        -
      </td>
    </tr>
    <tr>
      <td>kvmexits.bt</td>
      <td>Гипервизоры</td>
      <td>Причины выходов из виртуальной машины (VM Exits) в KVM.</td>
      <td><pre># kvmexits.bt
@exits[EXIT_REASON_EPT_VIOLATION]: 1200
@exits[EXIT_REASON_IO_INSTRUCTION]: 400
@exits[EXIT_REASON_HLT]: 150</pre></td>
      <td>
        -
      </td>
    </tr>
  </tbody>
</table>

## Заключение
Общей чертой рассмотренных инструментов является точечность. Каждая утилита нацелена на мониторинг конкретных аспектов работы системы. Не все из перечисленных утилит могут быть полезны в рамках тестирования производительности, инструменты по типу trace, funccount, memleak, capable, signals.bt, oomkill.bt и другие полезны для исследования поведения системы в конкретных сценариях и не подходят для оценки производительности в целом.

В рамках исследования производительности и стабильности операционных систем полезными могут оказаться утилиты по типу cpudist, cpustolen.bt, workq.bt, runqlen, runqlat и другие программы, собирающие и отображающие статистику о работе конкретных механизмов внутри тестируемой системы. Например, можно создать нагрузку на систему, после чего использовать один или несколько из упомянутых инструментов, чтобы оценить эффективность работы системы в данных условиях. Однако сами сценарии нагрузки, а также методы оценивания придется продумывать и реализовывать самостоятельно.

Таким образом, технология BPF (bcc и bpftrace в частности) предоставляет массу инструментов для отслеживания и трассировки производительности системы в самых разных аспектах. И хотя подобные утилиты являются весьма точечными и не подходят для масштабного тестирования производительности ОС, данная технология может оказаться весьма полезной для выявления и оптимизации узких мест в рамках конкретного сценария использования.

## Источники
[1] [BPF: профессиональная оценка производительности](https://books.yandex.ru/books/u9zq94NK)

[2] [BPF Compiler Collection (BCC)](https://github.com/iovisor/bcc/blob/master/README.md)

[3] [bpftrace tools](https://github.com/bpftrace/bpftrace/blob/master/tools/README.md)
