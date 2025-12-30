## Введение
BPF -- расшифровывается как Berkeley Packet Filter -- технология, состоящая из набора инструкций, вспомогательных типов данных и объектов, функционирующая на уровне ядра операционной системы. Также BPF определяет набор инструкций для виртуальной машины BPF, которые исполняются на уровне ядра, попадая сначала в верификатор, а затем в JIT (Just-in-time) компилятор. Другими словами, BPF -- это виртуальная машина, предоставляющая возможность взаимодействовать с механизмами операционной системы без необходимости подключать новые модули или пересборки OS.

Изначально BPF, разработанный еще в 1992 году, использовался для взаимодействия с сетевыми пакетами. Так, эта технология легла в основу такого сетевого инструмента как tcpdump. Изначальную утилиту принято обозначать как cBPF (где c - classic), а новую расширенную версию eBPF (e -- extended) либо просто BPF.

В последствии механизм BPF многократно расширялся и обновлялся, что превратило BPF в механизм выполнения общего назначения, который можно использовать для самых разных целей, включая создание продвинутых инструментов анализа производительности.

Важно отметить следующее -- BPF -- это набор инструментов для написание программ различного назначения, функционирующих на уровне операционной системы. Написание собственных программ-утилит не является первостепенной задачей текущего проекта. Поэтому сконцентрируемся на обзоре существующих утилит тестирования и анализа производительности на основе eBPF, а имено рассмотрим наборы утилит bcc и bpftrace.

## BCC
BCC (часто пишется просто bcc) -- BPF Compiler Collection, то есть коллекция компиляторов BPF, -- набор инструментов и библиотек для написания BPF программ, в том числе C++ и Python фронт-энды, а также набор готовых утилит для трассировки. Список доступных утилит представлен в виде таблицы:

|Область применения|Инструменты|
|--|--|
|Многоцелевые|trace, argdist, funccount, stackcount, opensnoop trace, argdist, funccount, stackcount, opensnoop|
|Процессор|execsnoop, runqlat, runqlen, cpudist, profile, offcputime, syscount, softirq, hardirq|
|Память|memleak|
|Файловая система|opensnoop, filelife, vfsstatt, fileslower, cachestat, writeback, dcstat, xfsslower, xfsdist, ext4dist|
|Ввод/вывод|biolatency, biosnoop, biotop, bitesize|
|Сети|tcpconnect, tcpaccept, tcplife, tcpretrans|
|Безопасность|capable|
|Языка|javastat, javacalls, javathreads, javaflow, javagc|
|Приложения|mysqld_qslower, signals, killsnoop|
|Ядро|wakeuptime, offwaketime|

Рассмотрим некоторые утилиты более детально.

### 1. trace
trace -- многофункциональный инструмент трассировки. Позволяет отслеживать вызов функций в пространстве пользователя, переданные аргументы, возвращаемое значение, трассировку стека функции и другое.

Пример использования функции:
```
# trace 'sys_read (arg3 > 20000) "read %d bytes", arg3'
PID    COMM         FUNC             -
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes
4490   dd           sys_read         read 1048576 bytes
```
Здесь мы "отлавливаем" операции чтения большого размера за счет отслеживания системного вызова на чтение, где arg3 -- количество байт на чтение.

С помощью trace можно также отлавливать пользовательские функции:
```
# trace 'r:bash:readline "%s", retval'
PID    COMM         FUNC             -
2740   bash         readline         echo hi!
2740   bash         readline         man ls
```
Кодовое слово *retval* обозначает возвращаемое значение.

### 2. cpudist
cpudist -- программа, которая суммирует время работы задач на CPU в виде гистограммы, показывающей, сколько времени обрабатывалась задача прежде чем была отменена в планировании (descheduled).

Базовый пример использования может выглядеть следующим образом:
```
# ./cpudist.py
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
     16384 -> 32767      : 3        |                                        |
```
По данной диаграмме можно понять, что большинство тасков в среднем исполнялось от 4 до 16 миллисекунд.

При необходимости можно ограничить вывод, оставив только распределение для задач от конкретного потока:
```
# ./cpudist.py -p $(pidof parprimes)
Tracing on-CPU time... Hit Ctrl-C to end.
^C
     usecs               : count     distribution
         0 -> 1          : 3        |                                        |
         2 -> 3          : 17       |                                        |
         4 -> 7          : 39       |                                        |
         8 -> 15         : 52       |*                                       |
        16 -> 31         : 43       |                                        |
        32 -> 63         : 12       |                                        |
        64 -> 127        : 13       |                                        |
       128 -> 255        : 0        |                                        |
       256 -> 511        : 1        |                                        |
       512 -> 1023       : 11       |                                        |
      1024 -> 2047       : 15       |                                        |
      2048 -> 4095       : 41       |                                        |
      4096 -> 8191       : 1134     |************************                |
      8192 -> 16383      : 1883     |****************************************|
     16384 -> 32767      : 65       |*                                       |
```

### 3. memleak
meamleak, как следует из названия, позволяет осуществлять трассировку выделения и очищения памяти, после чего обозначить места утечек памяти:
```
# ./memleak -p $(pidof allocs)
Attaching to pid 5193, Ctrl+C to quit.
[11:16:33] Top 2 stacks with outstanding allocations:
        80 bytes in 5 allocations from stack
                 main+0x6d [allocs]
                 __libc_start_main+0xf0 [libc-2.21.so]

[11:16:34] Top 2 stacks with outstanding allocations:
        160 bytes in 10 allocations from stack
                 main+0x6d [allocs]
                 __libc_start_main+0xf0 [libc-2.21.so]
```

### 4. cachetop
cachetop -- показывает статистику промахов/попаданий в кэше, а также процент попадания при чтении/записи для каждого процесса в виде таблицы (на подобие вывода команды *top*):
```
# ./cachetop 5
13:01:01 Buffers MB: 76 / Cached MB: 114 / Sort: HITS / Order: ascending
PID      UID      CMD              HITS     MISSES   DIRTIES  READ_HIT%  WRITE_HIT%
       1 root     systemd                 2        0        0     100.0%       0.0%
     680 root     vminfo                  3        4        2      14.3%      42.9%
     567 syslog   rs:main Q:Reg          10        4        2      57.1%      21.4%
     986 root     kworker/u2:2           10     2457        4       0.2%      99.5%
     988 root     kworker/u2:2           10        9        4      31.6%      36.8%
     877 vagrant  systemd                18        4        2      72.7%      13.6%
     983 root     python                148        3      143       3.3%       1.3%
     981 root     strace                419        3      143      65.4%       0.5%
     544 messageb dbus-daemon           455      371      454       0.1%       0.4%
     243 root     jbd2/dm-0-8           457      371      454       0.4%       0.4%
     985 root     (mount)               560     2457        4      18.4%      81.4%
     987 root     systemd-udevd         566        9        4      97.7%       1.2%
     988 root     systemd-cgroups       569        9        4      97.8%       1.2%
     986 root     modprobe              578        9        4      97.8%       1.2%
     287 root     systemd-journal       598      371      454      14.9%       0.3%
     985 root     mount                 692     2457        4      21.8%      78.0%
     984 vagrant  find                 9529     2457        4      79.5%      20.5%
```
(цифра 5 в команде -- значение задержки вывода в секундах)

### 5. biolatency
biolatency -- позволяет отслеживать время задержки устройства ввода/вывода в виде гистограммы:
```
# ./biolatency
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
   65536 -> 131071   : 2        |*                                     |
```

Задержка дискового ввода-вывода измеряется от момента отправки запроса на устройство до его завершения. Опция -Q может использоваться для включения времени ожидания в очереди ядра.

###  6. tcplife
tcpfile -- используется для сбора статистики tcp соединений в процессе трассировки:
```
# ./tcplife
PID   COMM       LADDR           LPORT RADDR           RPORT TX_KB RX_KB MS
22597 recordProg 127.0.0.1       46644 127.0.0.1       28527     0     0 0.23
3277  redis-serv 127.0.0.1       28527 127.0.0.1       46644     0     0 0.28
22598 curl       100.66.3.172    61620 52.205.89.26    80        0     1 91.79
22604 curl       100.66.3.172    44400 52.204.43.121   80        0     1 121.38
22624 recordProg 127.0.0.1       46648 127.0.0.1       28527     0     0 0.22
3277  redis-serv 127.0.0.1       28527 127.0.0.1       46648     0     0 0.27
22647 recordProg 127.0.0.1       46650 127.0.0.1       28527     0     0 0.21
3277  redis-serv 127.0.0.1       28527 127.0.0.1       46650     0     0 0.26
```

###  7. capable
capable -- отслеживает вызовы функции ядра `cap_capable()`, которая выполняет проверки безопасности, и выводит подробную информацию о каждом вызове. Например:
```
# ./capable.py
TIME      UID    PID    COMM             CAP  NAME                 AUDIT
22:11:23  114    2676   snmpd            12   CAP_NET_ADMIN        1
22:11:23  0      6990   run              24   CAP_SYS_RESOURCE     1
22:11:23  0      7003   chmod            3    CAP_FOWNER           1
22:11:23  0      7003   chmod            4    CAP_FSETID           1
22:11:23  0      7005   chmod            4    CAP_FSETID           1
22:11:23  0      7005   chmod            4    CAP_FSETID           1
22:11:23  0      7006   chown            4    CAP_FSETID           1
22:11:23  0      7006   chown            4    CAP_FSETID           1
22:11:23  0      6990   setuidgid        6    CAP_SETGID           1
22:11:23  0      6990   setuidgid        6    CAP_SETGID           1
22:11:23  0      6990   setuidgid        7    CAP_SETUID           1
22:11:24  0      7013   run              24   CAP_SYS_RESOURCE     1
22:11:24  0      7026   chmod            3    CAP_FOWNER           1
22:11:24  0      7026   chmod            4    CAP_FSETID           1
22:11:24  0      7028   chmod            4    CAP_FSETID           1
22:11:24  0      7028   chmod            4    CAP_FSETID           1
22:11:24  0      7029   chown            4    CAP_FSETID           1
22:11:24  0      7029   chown            4    CAP_FSETID           1
22:11:24  0      7013   setuidgid        6    CAP_SETGID           1
22:11:24  0      7013   setuidgid        6    CAP_SETGID           1
22:11:24  0      7013   setuidgid        7    CAP_SETUID           1
22:11:25  0      7036   run              24   CAP_SYS_RESOURCE     1
22:11:25  0      7049   chmod            3    CAP_FOWNER           1
22:11:25  0      7049   chmod            4    CAP_FSETID           1
22:11:25  0      7051   chmod            4    CAP_FSETID           1
22:11:25  0      7051   chmod            4    CAP_FSETID           1
```

###  8. wakeuptime
wakeuptime -- измеряет время блокировки потоков и отображает трассировки стека для потоков, выполнивших пробуждение, а также имена процессов пробуждающего и целевого процессов и общее время блокировки. Время блокировки измеряется с момента блокировки потока до момента отправки сигнала пробуждения.
```
# ./wakeuptime
Tracing blocked time (us) by kernel stack... Hit Ctrl-C to end.
^C
[...truncated...]

    target:          vmstat
    ffffffff810df082 hrtimer_wakeup
    ffffffff810df494 __hrtimer_run_queues
    ffffffff810dfba8 hrtimer_interrupt
    ffffffff8100b9e1 xen_timer_interrupt
    ffffffff810cb9c8 handle_irq_event_percpu
    ffffffff810cf1ca handle_percpu_irq
    ffffffff810cb0c2 generic_handle_irq
    ffffffff814766f7 evtchn_2l_handle_events
    ffffffff81473e83 __xen_evtchn_do_upcall
    ffffffff81475cf0 xen_evtchn_do_upcall
    ffffffff8178adee xen_do_hypervisor_callback
    waker:           swapper/1
        4000415

    target:          rcuos/7
    ffffffff810b5b12 autoremove_wake_function
    ffffffff810b5462 __wake_up_common
    ffffffff810b54d9 __wake_up
    ffffffff810d6f28 rcu_nocb_kthread
    ffffffff81092979 kthread
    ffffffff8178940f ret_from_fork
    waker:           rcuos/6
        4095781

    target:          rcuos/6
    ffffffff810b5b12 autoremove_wake_function
    ffffffff810b5462 __wake_up_common
    ffffffff810b54d9 __wake_up
    ffffffff810d8043 rcu_gp_kthread
    ffffffff81092979 kthread
    ffffffff8178940f ret_from_fork
    ffffffff81ca9420 ddebug_tables
    waker:           rcu_sched
        4101075
[...]
```
При расчете времени программа не включает некоторую задержку в очереди выполнения целевого потока, который может не выполниться мгновенно, если ему необходимо дождаться своей очереди.

## bpftrace
bpftrace — это трассировщик с открытым исходным кодом, основанный на BPF и BCC. Проект bpftrace, так же как BCC, включает множество инструментов оценки производительности с сопроводительной документацией. Он также предоставляет язык программирования высокого уровня, позволяющий писать мощные инструменты.

По аналогии с bcc, список доступных утилит можно отобразить в виде таблицы:
|Область применения|Инструменты|
|--|--|
|Многоцелевые|execsnoop.bt, threadsnoop.bt, opensnoop.bt, killsnoop.bt, signals.bt|
|Процессор|execsnoop.bt, runqlat.bt, runqlen.bt, cpuwalk.bt, offcputime.bt|
|Пямять|oomkill.bt, failts.bt, vmscan.bt, swapin.bt|
|Файловая система|vfsstat.bt, filelife.bt, xfsdist.bt|
|Вввод/вывод|biosnoop.bt, biolatency.bt, bitesize.bt, biostacks.bt, scsilatency.bt, nvmelatency.bt|
|Сети|tcpaccept.bt, tcpconnect.bt, tcpdrop.bt, tcpretrans.bt, gethostlatency.bt|
|Безопасность|ttysnoop.bt, elfsnoop.bt, setuids.bt|
|Языка|jnistacks.bt, javacalls.bt|
|Приложения|threadsnoop.bt, pmheld.bt, naptime.bt, mysqld_qslower.bt|
|Ядро|mlock.bt, mheld.bt, kmem,bt, kpages.bt, workq.bt|
|Контейнеры|pidnss.bt, blkthrot.bt|
|Гипервизоры|xenhyper.bt, cpustolen.bt, kvmexits.bt|

Рассмотрим некоторые инструменты подробнее.

### 1. signals.bt
signals -- трассирует сигналы, посылаемые процессам, и обобщает распределение сигналов по типам и процессам-получателям.
Пример:
```
# signals.bt
Attaching 3 probes...
Counting signals. Hit Ctrl-C to end.
^C
@[SIGNAL, PID, COMM] = COUNT
@[SIGKILL, 3022, sleep]: 1
@[SIGINT, 2997, signals.bt]: 1
@[SIGCHLD, 21086, bash]: 1
@[SIGSYS, 3014, ServiceWorker t]: 4
@[SIGALRM, 2903, mpstat]: 6
@[SIGALRM, 1882, Xorg]: 87
```

### 2. runqlen(.bt)
runqlen(.bt) -- инструмент BCC и bpftrace. Предназначенный для выборки длин очередей на выполнение, подсчета количества задач, ожидающих своей очереди, и представления полученной информации в виде линейной гистограммы:
```
# runqlen
Sampling run queue length... Hit Ctrl-C to end.
runqlen        : count     distribution
    0          : 47284    |****************************************|
    1          : 211      |                                        |
    2          : 28       |                                        |
    3          : 6        |                                        |
    4          : 4        |                                        |
    5          : 1        |                                        |
    6          : 1        |                                        |
```
Чтобы получить статистику для каждого процессора, можно использовать флаг -C:
```
# runqlen -C
Sampling run queue length... Hit Ctrl-C to end.
^C
cpu = 0
    runqlen        : count     distribution
        0          : 0        |                                        |
        1          : 0        |                                        |
        2          : 0        |                                        |
        3          : 551      |****************************************|
cpu = 1
     runqlen       : count     distribution
        0          : 41       |****************************************|
cpu = 2
     runqlen       : count     distribution
        0          : 126      |****************************************|
[...]
```

Этот инструмент можно использовать для дальнейшего исследования проблем с задержками в очереди на выполнение или для приближенной оценки

### 3. oomkill(.bt)
oomkill(.bt) -- инструмент BCC и bpftrace, трассирующий события OOM Killer и сообщающий дополнительные детали, такие как средние значения загрузки. Средние значения загрузки помогают получить более полное представление о состоянии системы на момент события нехватки памяти, показывая, насколько велика была нагрузка на систему.
Пример использования:
```
# oomkill
Tracing OOM kills... Ctrl-C to stop.
08:51:34 Triggered by PID 18601 ("perl"), OOM kill of PID 1165 ("java"), 18006224
pages, loadavg: 10.66 7.17 5.06 2/755 18643
[...]
```
Данный вывод сообщает следующее -- процесс с id 18601 запросил дополнительную память, из-за чего возникла нехватка памяти и процесс 1165 был остановлен.

Ниже приводится реализация oomkill для bpftrace:
```
#!/usr/local/bin/bpftrace
#include <linux/oom.h>
BEGIN {
    printf("Tracing oom_kill_process()... Hit Ctrl-C to end.\n");

}
kprobe:oom_kill_process {
    $oc = (struct oom_control *)arg1;
    time("%H:%M:%S ");
    printf("Triggered by PID %d (\"%s\"), ", pid, comm);
    printf("OOM kill of PID %d (\"%s\"), %d pages, loadavg: ",
        $oc->chosen->pid, $oc->chosen->comm, $oc->totalpages);
    cat("/proc/loadavg");
}
```

### 4. vfssize
vfssize -- выводит распределение времени выполнения операций чтения и записи в VFS в виде гистограмм, группируя данные по именам процессов и именам или типам файлов.
Пример использования:
```
# vfssize
Attaching 5 probes...
@[tomcat-exec-393, tomcat_access.log]:
[8K, 16K)             31 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[...]
@[kafka-producer-, TCP]:
[4, 8)              2061 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[8, 16)                0 |                                                    |
[16, 32)               0 |                                                    |
[32, 64)            2032 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ |
@[EVCACHE_..., FIFO]:
[1]                 6376 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[...]
@[grpc-default-wo, TCP]:
[4, 8)               101 |                                                    |
[8, 16)            12062 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[16, 32)            8217 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 |
[32, 64)            7459 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                    |
[64, 128)           5488 |@@@@@@@@@@@@@@@@@@@@@@@                             |
[128, 256)          2567 |@@@@@@@@@@@                                         |
[256, 512)         11030 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@     |
[512, 1K)           9022 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@              |
[1K, 2K)            6131 |@@@@@@@@@@@@@@@@@@@@@@@@@@                          |
[2K, 4K)            6276 |@@@@@@@@@@@@@@@@@@@@@@@@@@@                         |
[4K, 8K)            2581 |@@@@@@@@@@@                                         |
[8K, 16K)            950 |@@@@                                                |
[...]
```

### 5. sofamily
sofamily -- трассирует создание новых соединений с использованием системных вызовов accept и connect и обобщает информацию по именам процессов и семействам адресов.

Пример использования:
```
# sofamily.bt
Attaching 7 probes...
Tracing socket connect/accepts. Ctrl-C to end.
^C
@accept[sshd, 2, AF_INET]: 2
@accept[java, 2, AF_INET]: 420
@connect[sshd, 2, AF_INET]: 2
@connect[sshd, 10, AF_INET6]: 2
@connect[(systemd), 1, AF_UNIX]: 12
@connect[sshd, 1, AF_UNIX]: 34
@connect[java, 2, AF_INET]: 215
```
Утилита может пригодиться для определения характеристик рабочей нагрузки: количественной оценки приложенной нагрузки и поиска любых неожиданных случаев использования сокетов, требующих дальнейшего изучения.

### 6. elfsnoop
elfsnoop -- инструмент для отслеживания попыток запуска двоичных файлов в формате ELF (Executable and Linking Format -- формат исполняемых и компонуемых модулей), широко используемом в Linux.

Пример:
```
# elfsnoop.bt
Attaching 3 probes...
Tracing ELF loads. Ctrl-C to end
TIME     PID    INTERPRETER       FILE             MOUNT      INODE     RET
11:18:43 9022   /bin/ls           /bin/ls          /          29098068    0
11:18:45 9023   /tmp/ls           /tmp/ls          /          23462045    0
11:18:49 9029   /usr/bin/python   ./opensnoop.py   /          20190728    0
[...]
```
Данный инструмент трассирует функцию ядра load_elf_binary(), которая отвечает за загрузку программ ELF для выполнения. Оверхед на работу этого инструмента должен быть незначительным, так как эта функция вызывается не очень часто.

### 7. 
kmem -- отображает распределение памяти ядра и количество операций выделения памяти, средний размер выделенного блока и общее количество выделенных байтов. 

Пример:
```
# kmem.bt
Attaching 3 probes...
Tracing kmem allocation stacks (kmalloc, kmem_cache_alloc). Hit Ctrl-C to end.
^C
[...]
@bytes[
    kmem_cache_alloc+288
    getname_flags+79
    getname+18
    do_sys_open+285
    SyS_openat+20
, Xorg]: count 44, average 4096, total 180224
@bytes[
    __kmalloc_track_caller+368
    kmemdup+27
    intel_crtc_duplicate_state+37
    drm_atomic_get_crtc_state+119
    page_flip_common+51
, Xorg]: count 120, average 2048, total 245760
```

Операция выделения памяти может выполняться очень часто, что в нагруженных системах может вести к снижению производительности системы.

### 8. pidnss
pidnss -- подсчитывает переключения контекста между контейнерами по смене пространства имен PID. 

Пример:
```
# pidnss.bt
Attaching 3 probes...
Tracing PID namespace switches. Ctrl-C to end
^C
Victim PID namespace switch counts [PIDNS, nodename]:
@[0, ]: 2
@[4026532981, 6280172ea7b9]: 27
@[4026531836, bgregg-i-03cb3a7e46298b38e]: 28
```

Этот инструмент можно использовать, чтобы убедиться, нет ли проблемы конкуренции нескольких контейнеров за один процессор. 

## Заключение
Технология BPF предоставляет массу инструментов для отслеживания и трассировки производительности системы в самых разных аспектах. И хотя подобные утилиты являются весьма точечными и не подходят для масштабного тестирования производительности ОС, данная технология может оказаться весьма полезной для выявления и оптимизации узких мест в рамках конкретного сценария использования системы.

## Источники
[1] [BPF: профессиональная оценка производительности](https://books.yandex.ru/books/u9zq94NK)

[2] [BPF Compiler Collection (BCC)](https://github.com/iovisor/bcc/blob/master/README.md)

[3] [bpftrace tools](https://github.com/bpftrace/bpftrace/blob/master/tools/README.md)