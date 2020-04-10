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
import pprint

default_config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports/",
    "URI_LOG_DIR": "./log",
    "CONFIG_FILE_PATH": "./app.cfg",
    "LOG_FILE_PATH": "./app.log",
    "LOG_FORMAT": "[%(asctime)s] %(levelname).1s %(message)s",
    "LOG_DATETIME_FORMAT": "%Y.%m.%d %H:%M:%S"
}

# Готовим рутовый логгер котрый работает с дефолтовой конфигурацей до проверки --config
logging.basicConfig(filename=None, \
                level=logging.INFO, \
                format=default_config["LOG_FORMAT"], \
                datefmt=default_config["LOG_DATETIME_FORMAT"])

# Функция возвращает путь к лог файлу есть файл есть
def find_log_file(_log_path=default_config["LOG_FILE_PATH"]):
  if os.path.exists(_log_path):
    return _log_path
  else:
    logging.info("Can't find app log file, a stdout will be used")
    return None

# Функция поиска конфигурации, берет --config, 
# если нет - берет app.cfg, 
# если нет берет default_config
def find_config(_config=default_config):
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument("--config", default=_config["CONFIG_FILE_PATH"] ,help="You could specify configuration file")
  args=arg_parser.parse_args()
  config_file_path=args.config
  if os.path.exists(config_file_path):
    with open(config_file_path, encoding='UTF-8') as datafile:
      data = json.load(datafile)
      _config.update(data)
  return _config

# Определение даты создания исходя из имени лог файла
def convert_to_date(_str):
  _re=re.split('\.|-',_str)[4]
  return datetime.datetime.strptime(_re, '%Y%m%d')

# Ищем самый свежий файл по дате в названии файла
def find_last_url_log_file(_config=default_config):
  list_of_files = os.listdir(_config["URI_LOG_DIR"]) 
  dict_of_files = {_file: convert_to_date(_file) for _file in list_of_files}
  return _config["URI_LOG_DIR"] + '/' + max(dict_of_files, key=dict_of_files.get)

#Определяет есть ли отчёт по пути к последнему логу
def find_result_file(_path, _config=default_config):
    _date = convert_to_date(_path)
    report_path = _config["REPORT_DIR"] + "/report-" + datetime.datetime.strftime(_date, "%Y.%m.%d.") + "html"
    if os.path.exists(report_path):
      print(report_path)
      return report_path
    else:
      return None

def extract_data_from_file(_path):
  print(_path)
  if _path.endswith(".gz"):
    logfile = gzip.open(_path, mode="rt", encoding="utf_8")
  else:
    logfile = open(_path, mode="rt", encoding="utf_8")
  for line in logfile:
      yield line
  logfile.close()

def median(lst): 
  n = len(lst) 
  if n < 1: 
    return None 
  if n % 2 == 1: 
    return sorted(lst)[n//2] 
  else: 
    return sum(sorted(lst)[n//2-1:n//2+1])/2.0 

def save_result(dir_reports, data):
  result_list = [i[1] for i in data.items()]
  print(result_list)
  if os.path.isdir(dir_reports):
    with open(os.path.join(dir_reports, 'report.html'), 'r', encoding='utf-8') as template:
      now = datetime.datetime.strftime(datetime.datetime.now(), '%Y.%m.%d' )
      with open(os.path.join(dir_reports, f'report-{now}.html'), 'w', encoding='utf-8' ) as report:
        report.write(template.read().replace("$table_json", str(result_list)))

def main(default_config):

  #Берем походящую конфигурацию
  try:
    config=find_config()
  except:
    logging.exception("config file reading error")

  #Делаем логирование в указанное в файле конфигурации место, если такого места нет то в stdout
  logger=logging.getLogger("log_analyzer")
  logger.setLevel(logging.INFO)
  
  try: 
    logging_file=find_log_file()
    if logging_file:
      formatter = logging.Formatter(fmt=config["LOG_FORMAT"], datefmt=config["LOG_DATETIME_FORMAT"])
      if find_log_file():
        handler = logging.FileHandler(config["LOG_FILE_PATH"])
      else:
        handler = logging.StreamHandler(sys.stdout)
      handler.setFormatter(formatter)
      logger.addHandler(handler)
  except:
    logging.exception("logging file preparing error")
  
  try:
    url_Log_file = find_last_url_log_file(config)
  except:
    logger.info("finding last url log file error")

  try:
    result_file_path = find_result_file(url_Log_file)
    if result_file_path:
      logger.info("A result file already exists {}".format(result_file_path))
      return
  except:
    logger.info("finding result file error")
  
  logfile_re_pattern = r'^.*[GET|POST|HEAD]\s(.*)HTTP.*(\d+\.\d{3})$'

  urls_with_time_list={
    "url_hash" : {
      "url" : '',
      "count" : 0,
      "time" : [],
      "total_time" : 0
    }
  }

  sum_count = 0
  sum_time = 0

  try:
    data = extract_data_from_file(url_Log_file)
    for line in data:
      sum_count += 1
      print(sum_count)
      # if sum_count > 10000: break
      match = re.match(logfile_re_pattern, line)
      if match:
        url = str(match.group(1))
        url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]
        if False:
          continue
        else:
          time = float(match.group(2))
          sum_time += time
          if url_hash in urls_with_time_list:
            urls_with_time_list[url_hash]['count'] += 1
            urls_with_time_list[url_hash]['time'].append(time)
            urls_with_time_list[url_hash]['total_time'] += time
          else:
            urls_with_time_list[url_hash]={}
            urls_with_time_list[url_hash]['time'] = [time]
            urls_with_time_list[url_hash]['total_time'] = time
            urls_with_time_list[url_hash]['url'] = url
            urls_with_time_list[url_hash]['count'] = 1
    
    urls_with_time_list.pop('url_hash')

    # top_list = {"url" : 0}

    top_list = {
      "url_hash" : {
        "count" : 0,
        "count_perc" : 0,
        "time_sum" : 0,
        "time_perc" : 0, 
        "time_avg" : 0,
        "time_max" : 0,
        "time_med" : 0
      }
    }

    for i in range(1000):
      print(i)
      list_with_max = max(urls_with_time_list.items(), key = lambda x: x[1]["total_time"])
      hash_with_max_time = list_with_max[0]
      max_sum_time = list_with_max[1]["total_time"]
      time_list_from_max = urls_with_time_list[hash_with_max_time]["time"]
      top_list[hash_with_max_time] = {}
      top_list[hash_with_max_time]["count"] = urls_with_time_list[hash_with_max_time]["count"]
      top_list[hash_with_max_time]["count_perc"] = round(urls_with_time_list[hash_with_max_time]["count"]*100/sum_count, 2)
      top_list[hash_with_max_time]["time_sum"] = round(max_sum_time,3)
      top_list[hash_with_max_time]["time_perc"] = round(max_sum_time*100/sum_time,2)
      top_list[hash_with_max_time]["time_avg"] = round(max_sum_time/len(time_list_from_max),3)
      top_list[hash_with_max_time]["time_max"] = max(time_list_from_max)
      top_list[hash_with_max_time]["url"] = urls_with_time_list[hash_with_max_time]["url"]
      top_list[hash_with_max_time]["time_med"] = round(max_sum_time if len(time_list_from_max) == 1 else median(time_list_from_max), 3)
      urls_with_time_list.pop(hash_with_max_time)

    top_list.pop("url_hash")

    pprint.pprint(top_list)
    
    save_result(config["REPORT_DIR"], top_list)

  except:
    logger.exception("extract error")
 
  return logging.info("app successfully completed")

if __name__ == "__main__":
  try:
    main(default_config)
  except:
    logging.exception("unknown exception")