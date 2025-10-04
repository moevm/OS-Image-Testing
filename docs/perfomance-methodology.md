# Материалы об организации тестирования

## Существующие подходы к тестированию (образов ВМ)
1. [ссылка](https://www.researchgate.net/profile/Shravan-Pargaonkar/publication/375450774_A_Comprehensive_Review_of_Performance_Testing_Methodologies_and_Best_Practices_Software_Quality_Engineering/links/654a9cf8b1398a779d6e2125/A-Comprehensive-Review-of-Performance-Testing-Methodologies-and-Best-Practices-Software-Quality-Engineering.pdf)
* обзорная статья. перечислены методологии, есть общие советы по организации, анализу

2. [ссылка](https://www.researchgate.net/publication/347189472_Performance_Evaluation_of_Linux_Operating_Systems)
* статья со сравнением 3 дистрибутивов. есть описание методологии, перечислены использованные для тестирования средства

3. [ссылка](https://www.semanticscholar.org/paper/Experimental-Evaluation-of-Desktop-Operating-Vdovjak-Balen/4f7b15b09d34a179dccc9e07d520b9e3686a0ad0#paper-topics)
* исследование перформанса сети. конкретно винды, но часть используемых утилит кроссплатформенные. есть методология, анализ

4. [ссылка](https://www.semanticscholar.org/paper/Performance-Evaluation-of-Recent-Windows-Operating-Martinović-Balen/024bf93c616d1f9860101f2b2c1be420e7ac5199)
* описание методолгии есть. 

5. [ссылка](https://ojs.nbu.bg/index.php/YT/article/view/1150)
* для сети. приведены скрипты, то как визуализируют данные

6. [ссылка](https://www.researchgate.net/publication/328758049_Measuring_Software_Performance_on_Linux)
* есть такое в аннотации: В этом отчете мы обобщаем наш опыт о том, как следует измерять характеристики производительности программного обеспечения при работе в операционной системе Linux и на современном процессоре. В частности, (1) Мы предоставляем общий обзор аппаратных средств и функций операционной системы, которые могут оказать существенное влияние на синхронизацию и то, как они взаимодействуют, (2) мы определяем источники ошибок, которые необходимо контролировать для получения объективных результатов измерений, и (3) мы предлагаем настройки измерений. для Linux, чтобы свести к минимуму ошибки. 

7. [ссылка](https://docs.yandex.ru/docs/view?tm=1759573243&tld=ru&lang=en&name=Netflix_Linux_Perf_Analysis_60s.pdf&text=程建军%2C%202014%20Method%20for%20analyzing%20performance%20bottleneck%20of%20server%20in%20Linux%20system%20testing%20environment&url=https%3A%2F%2Fwww.brendangregg.com%2FArticles%2FNetflix_Linux_Perf_Analysis_60s.pdf&lr=2&mime=pdf&l10n=ru&sign=f2d642acf08d9de7a0011d4c55f6b866&keyno=0&nosw=1&serpParams=tm%3D1759573243%26tld%3Dru%26lang%3Den%26name%3DNetflix_Linux_Perf_Analysis_60s.pdf%26text%3D%25E7%25A8%258B%25E5%25BB%25BA%25E5%2586%259B%252C%2B2014%2BMethod%2Bfor%2Banalyzing%2Bperformance%2Bbottleneck%2Bof%2Bserver%2Bin%2BLinux%2Bsystem%2Btesting%2Benvironment%26url%3Dhttps%253A%2F%2Fwww.brendangregg.com%2FArticles%2FNetflix_Linux_Perf_Analysis_60s.pdf%26lr%3D2%26mime%3Dpdf%26l10n%3Dru%26sign%3Df2d642acf08d9de7a0011d4c55f6b866%26keyno%3D0%26nosw%3D1)
* есть перечисление некоторых утилит - как их использовать. 

8. [ссылка](https://core.ac.uk/download/pdf/234676929.pdf)
* обзорная статья. есть немного про методологию,  немного про практические советы 

9. [ссылка](http://72.249.104.214/papers/linuxcon2010-linux-monitoring.pdf)
* обзор, руководство по мониторингу подсистем. про использование встроенных утилит, сбор и анализ данных в реальном времени

10. [ссылка](https://cyberleninka.ru/article/n/testirovanie-operatsionnyh-sistem/viewer)
* обзорная. есть раздел про тестирование производительности

11. [ссылка](https://habr.com/ru/companies/yadro/articles/716220/)
* статья про тестирование СХД. есть примеры, советы по тестированию

12. [ссылка](https://habr.com/ru/articles/154235/)
* статья про измерение производительности диска. есть примеры, советы по тестированию, примеры ошибок 

13. [ссылка](https://www.browserstack.com/guide/performance-testing)
* обзорная

14. [ссылка](https://docs.yandex.ru/docs/view?tm=1759597468&tld=ru&lang=ru&name=Акиньшин%20А._%20Профессиональный%20бенчмарк.(2022).pdf&text=акиньшин%20а%20кластеризация%20для%20анализа%20производительности&url=https%3A%2F%2Fpubl.lib.ru%2FARCHIVES%2FB%2F%27%27Biblioteka_programmista%27%27_(seriya)%2F%25C0%25EA%25E8%25ED%25FC%25F8%25E8%25ED%2520%25C0._%2520%25CF%25F0%25EE%25F4%25E5%25F1%25F1%25E8%25EE%25ED%25E0%25EB%25FC%25ED%25FB%25E9%2520%25E1%25E5%25ED%25F7%25EC%25E0%25F0%25EA.(2022).pdf&lr=2&mime=pdf&l10n=ru&sign=6e3842e309e28542d8630b1f41b6b636&keyno=0&nosw=1&serpParams=tm%3D1759597468%26tld%3Dru%26lang%3Dru%26name%3D%25D0%2590%25D0%25BA%25D0%25B8%25D0%25BD%25D1%258C%25D1%2588%25D0%25B8%25D0%25BD%2520%25D0%2590._%2520%25D0%259F%25D1%2580%25D0%25BE%25D1%2584%25D0%25B5%25D1%2581%25D1%2581%25D0%25B8%25D0%25BE%25D0%25BD%25D0%25B0%25D0%25BB%25D1%258C%25D0%25BD%25D1%258B%25D0%25B9%2520%25D0%25B1%25D0%25B5%25D0%25BD%25D1%2587%25D0%25BC%25D0%25B0%25D1%2580%25D0%25BA.(2022).pdf%26text%3D%25D0%25B0%25D0%25BA%25D0%25B8%25D0%25BD%25D1%258C%25D1%2588%25D0%25B8%25D0%25BD%2B%25D0%25B0%2B%25D0%25BA%25D0%25BB%25D0%25B0%25D1%2581%25D1%2582%25D0%25B5%25D1%2580%25D0%25B8%25D0%25B7%25D0%25B0%25D1%2586%25D0%25B8%25D1%258F%2B%25D0%25B4%25D0%25BB%25D1%258F%2B%25D0%25B0%25D0%25BD%25D0%25B0%25D0%25BB%25D0%25B8%25D0%25B7%25D0%25B0%2B%25D0%25BF%25D1%2580%25D0%25BE%25D0%25B8%25D0%25B7%25D0%25B2%25D0%25BE%25D0%25B4%25D0%25B8%25D1%2582%25D0%25B5%25D0%25BB%25D1%258C%25D0%25BD%25D0%25BE%25D1%2581%25D1%2582%25D0%25B8%26url%3Dhttps%253A%2F%2Fpubl.lib.ru%2FARCHIVES%2FB%2F%2527%2527Biblioteka_programmista%2527%2527_%2528seriya%2529%2F%2525C0%2525EA%2525E8%2525ED%2525FC%2525F8%2525E8%2525ED%252520%2525C0._%252520%2525CF%2525F0%2525EE%2525F4%2525E5%2525F1%2525F1%2525E8%2525EE%2525ED%2525E0%2525EB%2525FC%2525ED%2525FB%2525E9%252520%2525E1%2525E5%2525ED%2525F7%2525EC%2525E0%2525F0%2525EA.%25282022%2529.pdf%26lr%3D2%26mime%3Dpdf%26l10n%3Dru%26sign%3D6e3842e309e28542d8630b1f41b6b636%26keyno%3D0%26nosw%3D1)
* книга
---------
15. [ссылка](https://ieeexplore.ieee.org/abstract/document/10062997/metrics#metrics)
* нужно получать доступ
16. [ссылка](https://link.springer.com/book/10.1007/978-1-4842-7255-8)
* платная книга про тестирование производительности
17. [ссылка](https://ieeexplore.ieee.org/abstract/document/5544096)
* нужно получать доступ. по аннотации про тестирование производительности на основе системного ядра (в том числе способы создания рабочей нагрузки, тестирования сетевой нагрузки, тестирования нагрузки на ввод-вывод и получения системных параметров)
18. [ссылка](https://www.semanticscholar.org/paper/Analysis-of-Linux-Kernel’s-Real-Time-Performance-Zhang-Ran/7053457cff1b12d31e87d72363ccdaf31a874e26)
* нужно получать доступ. может быть, подходит



## Методика сравнения множества результатов между одинаковыми версиями образов, а также между разными версиями образов.
1. [ссылка](https://www.researchgate.net/publication/347189472_Performance_Evaluation_of_Linux_Operating_Systems)
* из первого раздела статья со сравнением 3 дистрибутивов (2). есть описание методологии. можно немного и на подход к сравнению результатов посмотреть
2. [ссылка](https://grafana.com/docs/grafana-cloud/testing/k6/analyze-results/test-comparison/)
* про Grafana
3. [ссылка](https://www.dotcom-monitor.com/wiki/ru/knowledge-base/сравнение-отчетов-о-нагрузочных-тест/)
* аналогично (2). но тут какое-то другое средство визуализации LoadView вместо Grafana
4. [ссылка](https://bencher.dev/)
* как я понимаю, можно использовать то, что в bencher можно сравнивать данные по веткам, стендам


## Поискать возможное использование методов кластеризации и визуализации кластеров для дальнейшего
1. [ссылка](https://docs.yandex.ru/docs/view?tm=1759596316&tld=ru&lang=ru&name=Andrey_Akinshin_-_Let_s_talk_about_performance_testing.pdf&text=применение%20кластеризации%20для%20анализа%20данных%20перформанс%20тестов&url=https%3A%2F%2Fassets.ctfassets.net%2F9n3x4rtjlya6%2F2hDW7Kf9gAy8Oay2Mq0wKo%2F30f6f48ae7630ab2b4aaad5f4eea16b5%2FAndrey_Akinshin_-_Let_s_talk_about_performance_testing.pdf&lr=2&mime=pdf&l10n=ru&sign=a29056e98eafa05dc18db7efed0a56de&keyno=0&nosw=1&serpParams=tm%3D1759596316%26tld%3Dru%26lang%3Dru%26name%3DAndrey_Akinshin_-_Let_s_talk_about_performance_testing.pdf%26text%3D%25D0%25BF%25D1%2580%25D0%25B8%25D0%25BC%25D0%25B5%25D0%25BD%25D0%25B5%25D0%25BD%25D0%25B8%25D0%25B5%2B%25D0%25BA%25D0%25BB%25D0%25B0%25D1%2581%25D1%2582%25D0%25B5%25D1%2580%25D0%25B8%25D0%25B7%25D0%25B0%25D1%2586%25D0%25B8%25D0%25B8%2B%25D0%25B4%25D0%25BB%25D1%258F%2B%25D0%25B0%25D0%25BD%25D0%25B0%25D0%25BB%25D0%25B8%25D0%25B7%25D0%25B0%2B%25D0%25B4%25D0%25B0%25D0%25BD%25D0%25BD%25D1%258B%25D1%2585%2B%25D0%25BF%25D0%25B5%25D1%2580%25D1%2584%25D0%25BE%25D1%2580%25D0%25BC%25D0%25B0%25D0%25BD%25D1%2581%2B%25D1%2582%25D0%25B5%25D1%2581%25D1%2582%25D0%25BE%25D0%25B2%26url%3Dhttps%253A%2F%2Fassets.ctfassets.net%2F9n3x4rtjlya6%2F2hDW7Kf9gAy8Oay2Mq0wKo%2F30f6f48ae7630ab2b4aaad5f4eea16b5%2FAndrey_Akinshin_-_Let_s_talk_about_performance_testing.pdf%26lr%3D2%26mime%3Dpdf%26l10n%3Dru%26sign%3Da29056e98eafa05dc18db7efed0a56de%26keyno%3D0%26nosw%3D1)
* презентация. есть раздел с кластеризацией. но без пояснений. может натолкнуть на мысли (?)
2. [ссылка](https://habr.com/ru/companies/jugru/articles/527186/)
* тут не про кластрезиацию, а просто про анализ

## Каким образом производят сохранение результатов тестирования и куда. в первую очередь упор на способы, которые позволяют далее обрабатывать такую информацию с помощью ПО
1. [ссылка](https://blog.octoperf.com/performance-test-results-trend-analysis/)
* про хранение данных в реляционную бд. есть и про анализ результатов, хранимых таким образом 
2. [ссылка](https://www.performance-lab.ru/blog/instrumenty-dlya-raspredelennogo-nagruzochnogo-testirovaniya)
* обзор разных инструментов. есть раздел со сбором метрик, визуализацией
3. [ссылка](https://www.researchgate.net/publication/325174187_Monitoring_and_Predicting_Linux_Server_Performance_With_Linear_Regression)
* рассказано, как с Prometheus и Grafana организовано. Про регрессию и анализ есть.
4. [ссылка](https://bencher.dev/docs/how-to/track-custom-benchmarks/)
* так можно в bencher с помощью JSON в формате Bencher Metric Format (BMF) полученные нами результаты загружать, как я понимаю

