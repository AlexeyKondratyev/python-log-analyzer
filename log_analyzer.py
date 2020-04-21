#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short
#   '$remote_addr  $remote_user $http_x_real_ip'
#   '[$time_local] "$request" '
#   '$status $body_bytes_sent "$http_referer" '
#   '"$http_user_agent" "$http_x_forwarded_for"'
#   '"$http_X_REQUEST_ID" "$http_X_RB_USER" '
#   '$request_time';

import os
import argparse
import logging
import json
import re
import datetime
import gzip
import hashlib
import unittest
import shutil
import sys
import time

default_config = {
    "REPORT_SIZE": 1000,
    "ERROR_LIMIT_PERC": 10,
    "REPORT_DIR": "./reports/",
    "URL_LOG_DIR": "./log/",
    "CONFIG_FILE_FULL_PATH": "./app.cfg",
    "LOG_FILE_FULL_PATH": "./app.log",
    "LOG_FORMAT": "[%(asctime)s] %(levelname).1s %(message)s",
    "LOG_DATETIME_FORMAT": "%Y.%m.%d %H:%M:%S"
}

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

# Берем полный путь файл конфигурации в --config
def check_config_from_cli(config):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--config",
                            default=config["CONFIG_FILE_FULL_PATH"],
                            help="You could specify configuration file, \
                                look at app.cfg.example")
    args = arg_parser.parse_args()
    if args.config:
        return args.config


# Парсим то что в файле и перезаписываем сопадающие в default_config ключи
def config_parsing(path):
    if os.path.exists(path):
        with open(path, encoding='UTF-8') as datafile:
            return json.load(datafile)


def logging_init(name, fmt, datefmt, path):
    logger = logging.getLogger(name)
    formatter = logging.Formatter(fmt=fmt,
                                  datefmt=datefmt)
    if os.path.exists(path):
        handler = logging.FileHandler(path)
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


# Вспомогательная функция для матчинга имен файлов
def match_date(re_template, _str):
    match = re.match(re_template, _str)
    if match:
        return match.group(1)


def log_file_existence_check(path):
    if not os.path.isdir(path):
        return None
# Ищем самый свежий файл по дате в названии файла
    re_template = r'^nginx-access-ui\.log-(\d{8})\..*$'
    files = {f: match_date(re_template, f) for f in os.listdir(path)}
    if files:
        match_name = max(files, key=files.get)
        full_path = path + match_name
        return full_path, files[match_name]


def report_existence_check(log_path,re_date):
    # now = datetime.datetime.strftime(datetime.datetime.now(), '%Y.%m.%d')
    # report_file = os.path.join(log_path, f'report-{now}.html')
    date_from_log = "{}.{}.{}".format(re_date[:4],re_date[4:6],re_date[6:8])
    report_file = os.path.join(log_path, f'report-{date_from_log}.html')
    if os.path.isfile(report_file):
        return report_file


def get_line_from_file(path):
    if path.endswith(".gz"):
        logfile = gzip.open(path, mode="rt", encoding="utf_8")
    else:
        logfile = open(path, mode="rt", encoding="utf_8")
    for line in logfile:
        yield line
    logfile.close()


# Генератор для получения строк из файла
@timeit
def log_file_parsing(path):
    logfile_re_pattern = r'^.*[GET|POST|HEAD]\s(.*)HTTP.*(\d+\.\d{3})$'
    urls_error_count = 0
    urls_count = 0
    urls_total_time = 0
    urls = {"url_hash":
            {"url": '',
             "count": 0,
             "time": [],
             "total_time": 0
             }
            }
# Парсим строки и считаем ошибки
    for line in get_line_from_file(path):
        urls_count += 1
        # if url_count > 10000: break
        match = re.match(logfile_re_pattern, line)
        if not match:
            urls_error_count += 1
        else:
            url = str(match.group(1))
            url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]
            # url_hash = url
            time = float(match.group(2))
            urls_total_time += time

        if url_hash in urls:
            urls[url_hash]['count'] += 1
            urls[url_hash]['time'].append(time)
            urls[url_hash]['total_time'] += time
        else:
            _dict = {'count': 1,
                     'url': url,
                     'total_time': time,
                     'time': [time]
                     }
            urls[url_hash] = _dict
    urls.pop('url_hash')
    error_perc = round(urls_error_count * 100 / urls_count, 4)
    return urls, urls_count, urls_total_time, error_perc


def median(lst):
    n = len(lst)
    if n < 1:
        return None
    if n % 2 == 1:
        return sorted(lst)[n//2]
    else:
        return sum(sorted(lst)[n//2-1:n//2+1])/2.0

@timeit
def get_top_requests(urls, urls_count, urls_total_time, report_size):
    # Выбираем топ запросов по time после парсинга
    _top = {
        "url_hash": {
            "count": 0,
            "count_perc": 0,
            "time_sum": 0,
            "time_perc": 0,
            "time_avg": 0,
            "time_max": 0,
            "time_med": 0,
            "url": " "
        }
    }
    for _ in range(report_size):
        _max = max(urls.items(), key=lambda x: x[1]["total_time"])
        _max_hash = _max[0]
        _max_max_time = _max[1]["total_time"]
        _max_time_list = urls[_max_hash]["time"]
        _dict = {
            "count": urls[_max_hash]["count"],
            "count_perc": round(urls[_max_hash]["count"]*100/urls_count, 2),
            "time_sum": round(_max_max_time, 3),
            "time_perc": round(_max_max_time*100/urls_total_time, 2),
            "time_avg": round(_max_max_time/len(_max_time_list), 3),
            "time_max": max(_max_time_list),
            "url": urls[_max_hash]["url"],
            "time_med": round(median(_max_time_list), 3)
        }
        _top[_max_hash] = _dict
    urls.pop(_max_hash)
    _top.pop("url_hash")
    return _top


# Переводим в данные в список json
def report_saving(dir_reports, data, re_date):
    result_list = [i[1] for i in data.items()]
    print(result_list)
    if os.path.isdir(dir_reports):
        tmp_file = os.path.join(dir_reports, 'report.tmp')
        # now = datetime.datetime.strftime(datetime.datetime.now(), '%Y.%m.%d')
        # report_file = os.path.join(dir_reports, f'report-{now}.html')
        date_from_log = "{}.{}.{}".format(re_date[:4],re_date[4:6],re_date[6:8])
        report_file = os.path.join(dir_reports, f'report-{date_from_log}.html')
        with open(os.path.join(dir_reports, 'report.html'), 'r',
                  encoding='utf-8') as template:
            with open(tmp_file, 'w', encoding='utf-8') as tmp:
                tmp.write(template.read().replace("$table_json",
                                                  str(result_list)))
        os.system('cp {} {}'.format(tmp_file, report_file))
        os.remove(tmp_file)


def main(config):
    # Проверяем есть ли что в --config, если нет - выходим
    config_file_path = check_config_from_cli(default_config)
    if config_file_path:
        # Пробуем парсить файл, если ничего нет - выходим
        parsed_config = config_parsing(config_file_path)
        if parsed_config:
            config.update(parsed_config)
            print("file config is used")
        else:
            print("cant parsing file")
            sys.exit(0)
    else:
        print("can'f find config file")
        sys.exit(0)

    # Настраиваем логирование
    logger = logging_init("log_analyzer",
                          config["LOG_FORMAT"],
                          config["LOG_DATETIME_FORMAT"],
                          config["LOG_FILE_FULL_PATH"]
                          )

    # Ищем последний файл лога, если ничего не нашли выходим
    if not log_file_existence_check(config["URL_LOG_DIR"]):
        logger.exception("log file not found")
        sys.exit(0)

    # Проверяем есть ли уже файл отчёта с сегодняшней датой, если есть выходим
    log_file_full_path, log_re_date = log_file_existence_check(config["URL_LOG_DIR"])
    if report_existence_check(config["REPORT_DIR"], log_re_date):
        logger.exception("report already exists")
        sys.exit(0)

    # Парсим файл, если ошибик больше чем ERROR_LIMIT, выходим
    logger.info("log file parsing")
    data, count, total_time, error_perc = log_file_parsing(log_file_full_path)

    if error_perc > config["ERROR_LIMIT_PERC"]:
        logger.exception("error limit exceeded")
        sys.exit(0)
    else:
        logger.info("error limit perc {}". format(error_perc))

    # Выбираем топ запросов по суммарныму времени обработки
    logger.info("top forming")
    top_requests = get_top_requests(data, count, total_time,
                                config["REPORT_SIZE"])

    # Сохраняем отчёт
    report_saving(config["REPORT_DIR"], top_requests, log_re_date)


if __name__ == "__main__":
    try:
        main(default_config)
    except:
        logging.exception("unknown exception")
