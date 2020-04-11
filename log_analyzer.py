#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

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

default_config = {
    "REPORT_SIZE": 1000,
    "ERROR_LIMIT_PERC" : 10,
    "REPORT_DIR": "./reports/",
    "URL_LOG_DIR": "./log/",
    "CONFIG_FILE_FULL_PATH" : "./app.cfg",
    "LOG_FILE_FULL_PATH": "./app.log",
    "LOG_FORMAT": "[%(asctime)s] %(levelname).1s %(message)s",
    "LOG_DATETIME_FORMAT": "%Y.%m.%d %H:%M:%S"
}

# Готовим рутовый логгер котрый работает с дефолтовой конфигурацей до проверки --config
# logging.basicConfig(filename=None, \
#                 level=logging.INFO, \
#                 format=default_config["LOG_FORMAT"], \
#                 datefmt=default_config["LOG_DATETIME_FORMAT"])

# # Функция возвращает путь к лог файлу есть файл есть
# def find_log_file(_log_path=default_config["LOG_FILE_PATH"]):
#   if os.path.exists(_log_path):
#     return _log_path
#   else:
#     logging.info("Can't find app log file, a stdout will be used")
#     return None

# Функция поиска конфигурации, берет --config, 
# если нет - берет app.cfg, 
# если нет берет default_config
# def find_config(_config=default_config):
#   arg_parser = argparse.ArgumentParser()
#   arg_parser.add_argument("--config", default=_config["CONFIG_FILE_PATH"] ,help="You could specify configuration file")
#   args=arg_parser.parse_args()
#   config_file_path=args.config
#   if os.path.exists(config_file_path):
#     with open(config_file_path, encoding='UTF-8') as datafile:
#       data = json.load(datafile)
#       _config.update(data)
#   return _config

# # Определение даты создания исходя из имени лог файла
# def convert_to_date(_str):
#   _re=re.split('\.|-',_str)[4]
#   return datetime.datetime.strptime(_re, '%Y%m%d')

# # Ищем самый свежий файл по дате в названии файла
# def find_last_url_log_file(_config=default_config):
#   list_of_files = os.listdir(_config["URI_LOG_DIR"]) 
#   dict_of_files = {_file: convert_to_date(_file) for _file in list_of_files}
#   return _config["URI_LOG_DIR"] + '/' + max(dict_of_files, key=dict_of_files.get)

# #Определяет есть ли отчёт по пути к последнему логу
# def find_result_file(_path, _config=default_config):
#     _date = convert_to_date(_path)
#     report_path = _config["REPORT_DIR"] + "/report-" + datetime.datetime.strftime(_date, "%Y.%m.%d.") + "html"
#     if os.path.exists(report_path):
#       print(report_path)
#       return report_path
#     else:
#       return None

# def extract_data_from_file(_path):
#   print(_path)
#   if _path.endswith(".gz"):
#     logfile = gzip.open(_path, mode="rt", encoding="utf_8")
#   else:
#     logfile = open(_path, mode="rt", encoding="utf_8")
#   for line in logfile:
#       yield line
#   logfile.close()

# def save_result(dir_reports, data):
#   result_list = [i[1] for i in data.items()]
#   print(result_list)
#   if os.path.isdir(dir_reports):
#     with open(os.path.join(dir_reports, 'report.html'), 'r', encoding='utf-8') as template:
#       now = datetime.datetime.strftime(datetime.datetime.now(), '%Y.%m.%d' )
#       with open(os.path.join(dir_reports, f'report-{now}.html'), 'w', encoding='utf-8' ) as report:
#         report.write(template.read().replace("$table_json", str(result_list)))
##########################################################################

def check_config_from_cli(config):
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument("--config", default=config["CONFIG_FILE_FULL_PATH"] ,help="You could specify configuration file, look at app.cfg.example")
  args = arg_parser.parse_args()
  if os.path.exists(args.config):
    with open(args.config, encoding='UTF-8') as datafile:
      return config.update(json.load(datafile))
  else:
   return False

def report_existence_check(path):
  
  def match_date(_str):
    match = re.match(r'^report-(\d{4}\.\d{2}\.\d{2})\.html$', _str)
    if match:
      return match.group(1)
    else:
      return False
  
  if not os.path.isdir(path):
    return False
  files = {f: match_date(f) for f in os.listdir(path)}
  for name, date in files.items():
    if date == datetime.datetime.strftime(datetime.datetime.now(),'%Y.%m.%d'):
      return name
  return False

    # match = re.match(r'^report-(\d{4}\.\d{2}\.\d{2})\.html$', f)
    # # if os.path.exists(config_file_path):
    # if match and match.group(1) == datetime.datetime.strftime(datetime.datetime.now(),'%Y.%m.%d'):
    #   return True
    # else:
    #   return False

def log_file_existence_check(path):

  def match_date(_str):
    match = re.match(r'^nginx-access-ui\.log-(\d{8})\..*$', _str)
    return match.group(1)

  if not os.path.isdir(path):
    return False
  # Ищем самый свежий файл по дате в названии файла
  files = {f: match_date(f) for f in os.listdir(path)}
  if files:
    return path + max(files, key=files.get)
  else:
    return False

def log_file_parsing(path):
  # Генератор для получения строк из файла
  def get_line_from_file():
    if path.endswith(".gz"):
      logfile = gzip.open(path, mode="rt", encoding="utf_8")
    else:
      logfile = open(path, mode="rt", encoding="utf_8")
    for line in logfile:
      yield line
    logfile.close()
  
  logfile_re_pattern = r'^.*[GET|POST|HEAD]\s(.*)HTTP.*(\d+\.\d{3})$' 
  urls_error_count = 0 
  urls_count = 0
  urls_total_time = 0
  urls={"url_hash" : {"url" : '', "count" : 0, "time" : [], "total_time" : 0}}
  
  # Парсим строки и считаем ошибки
  for line in get_line_from_file():
    urls_count += 1
    # if url_count > 10000: break
    match = re.match(logfile_re_pattern, line)
    if not match: urls_error_count += 1
    else:
      url = str(match.group(1))
      url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]
      time = float(match.group(2))
      urls_total_time += time
    
    if url_hash in urls:
      urls[url_hash]['count'] += 1
      urls[url_hash]['time'].append(time)
      urls[url_hash]['total_time'] += time
    else:
      _dict = {'count': 1, 'url' : url, 'total_time' : time, 'time' : [time]}
      urls[url_hash] = _dict
  urls.pop('url_hash')
  error_perc = round(urls_error_count * 100 / urls_count, 4)
  return urls, urls_count, urls_total_time, error_perc

def get_top_requests(urls, urls_count, urls_total_time, report_size):
  # Функция для нахождения медианы
  def median(lst): 
    n = len(lst) 
    if n < 1: 
      return None 
    if n % 2 == 1: 
      return sorted(lst)[n//2] 
    else: 
      return sum(sorted(lst)[n//2-1:n//2+1])/2.0 
  # Выбираем топ запросов по time после парсинга
  _top = { 
    "url_hash" : {
      "count" : 0,
      "count_perc" : 0,
      "time_sum" : 0,
      "time_perc" : 0, 
      "time_avg" : 0,
      "time_max" : 0,
      "time_med" : 0,
      "url" : " "
    }
  }
  for _ in range(report_size):
    _max = max(urls.items(), key = lambda x: x[1]["total_time"])
    _max_hash = _max[0]
    _max_max_time = _max[1]["total_time"]
    _max_time_list = urls[_max_hash]["time"]
    _dict = {
      "count" : urls[_max_hash]["count"],
      "count_perc" : round(urls[_max_hash]["count"]*100/urls_count, 2),
      "time_sum" : round(_max_max_time ,3),
      "time_perc" : round(_max_max_time*100/urls_total_time,2),
      "time_avg" : round(_max_max_time/len( _max_time_list),3),
      "time_max" : max(_max_time_list),
      "url" : urls[_max_hash]["url"],
      "time_med" : round(_max_max_time if len(_max_time_list) == 1 else median(_max_time_list), 3)
    }
    _top[_max_hash] =_dict 
    urls.pop(_max_hash)
  _top.pop("url_hash")
  return _top

def report_saving(dir_reports, data):
  #Переводим в данные в список json
  result_list = [i[1] for i in data.items()]
  if os.path.isdir(dir_reports):
    tmp_file = os.path.join(dir_reports, 'report.tmp')
    now = datetime.datetime.strftime(datetime.datetime.now(), '%Y.%m.%d' )
    report_file = os.path.join(dir_reports, f'report-{now}.html')

    with open(os.path.join(dir_reports, 'report.html'), 'r', encoding='utf-8') as template:  
      # with open(os.path.join(dir_reports, f'report-{now}.html'), 'w', encoding='utf-8' ) as report:
      with open(tmp_file, 'w', encoding='utf-8' ) as tmp:  
        tmp.write(template.read().replace("$table_json", str(result_list)))
    os.system('cp {} {}'.format(tmp_file, report_file))
    os.remove(tmp_file) 
  else:
    return False

#########################################################################################

def main(default_config):
  # Пытаемся прочитать конфигурацию из файла указанного в --config
  # Если не получилось прочитать конигурацию из файлов берем конфиг из программы
  if check_config_from_cli(default_config):
    config = check_config_from_cli(default_config)
    sys.stdout.write("file config is used\n")
  else:
    config=default_config
    sys.stdout.write("default config is used\n")
  
  # Настриваем логирование
  logger=logging.getLogger("log_analyzer")
  formatter = logging.Formatter(fmt=config["LOG_FORMAT"], datefmt=config["LOG_DATETIME_FORMAT"])
  if os.path.exists(config["LOG_FILE_FULL_PATH"]):
    handler = logging.FileHandler(config["LOG_FILE_FULL_PATH"])
  else:
    handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.setLevel(logging.INFO)

  # Проверяем есть ли уже файл отчёта с сегодняшней датой, если есть выходим
  if report_existence_check(config["REPORT_DIR"]):
    logger.exception("report already exists")
    sys.exit(0)

  # Ищем последний файл лога, если ничего не нашли выходим
  if not log_file_existence_check(config["URL_LOG_DIR"]):
    logger.exception("log file not found")
    sys.exit(0)

  # Парсим файл, если ошибик больше чем ERROR_LIMIT, выходим
  log_file_full_path = log_file_existence_check(config["URL_LOG_DIR"])
  logger.info("log file parsing")

  data, count, total_time, error_perc = log_file_parsing(log_file_full_path)

  if error_perc > config["ERROR_LIMIT_PERC"]:
    logger.exception("error limit exceeded")
    sys.exit(0)
  else:
    logger.info("error limit perc {}". format(error_perc))

  # Выбираем топ запросов по суммарныму времени обработки
  logger.info("top forming")
  top_requests = get_top_requests(data, count, total_time, config["REPORT_SIZE"])

  # Сохраняем отчёт
  report_saving(config["REPORT_DIR"], top_requests)


class AppTest(unittest.TestCase):
    def test_check_config_from_cli(self):
        self.assertRegex(self, check_config_from_cli(default_config), r'.*REPORT_DIR.*' )

if __name__ == "__main__":
  try:
    unittest.main(default_config)
  except:
    logging.exception("unknown exception")