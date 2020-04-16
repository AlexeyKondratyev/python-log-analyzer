# Анализ лог файлов nginx

## Требование к источнику данных

- Папка по-умолчанию ./log
- Формат имени файла nginx-access-ui.log-<%Y%m%d>.gz
- Выбирается файл с максимльной датой в имени (%Y%m%d)
- Допустимы как .gz формат так и текстовый (без расширения)
- Формат лога:

'''
log_format ui_short
  '$remote_addr  $remote_user $http_x_real_ip'
  '[$time_local] "$request" '
  '$status $body_bytes_sent "$http_referer" '
  '"$http_user_agent" "$http_x_forwarded_for"'
  '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
  '$request_time';
'''

## Файл конфигурации

Конфигурация осуществляется путём передачи файла формата json через `--config`.

- "REPORT_SIZE" - количество ссылок в отчёте (по умолчанию - 1000);
- "REPORT_DIR" - путь для сохранения отчётов (по умолчанию - "./reports");
- "LOG_DIR" - путь для поиска логов (по умолчанию - "./log");
- "CONFIG_DIR" - путь для файлов кофигурации (по умолчанию - "./app.cfg");
- "LOGGING_FILE" - путь файла логгирования (по умолчанию - "./app.log");
- "ERROR_LIMIT_PERC" - ограничение на количество ошибок в файле в процентах (по умолчанию - 10).

## Тестирование

Запустить тест можно

'''bash
python3  test.py
'''

## Запуск приложения

'''
cp app.cfg.example app.cfg
python3  log_analyzer.py --config app.cfg
'''

## Отчёт
* count - сколько раз встречается URL, абсолютное значение;
* count_perc - сколько раз встречается URL, в процентнах относительно общего числа запросов;
* time_sum - суммарный \$request_time для данного URL'а, абсолютное значение;
* time_perc - суммарный \$request_time для данного URL'а, в процентах относительно общего $request_time всех запросов;
* time_avg - средний \$request_time для данного URL'а;
* time_max - максимальный \$request_time для данного URL'а;
* time_med - медиана \$request_time для данного URL'а.
