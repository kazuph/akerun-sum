﻿# -*- coding: utf-8 -*-

import math
import calendar
import datetime
import codecs
import csv
import sys
import os

DAYSTART = '0300'
ROUNDDOWNTIME = 15

def option_parser():
  usage = 'Usage: python {} [-i <input filename>] [-o <output filename>] [-d <period(yyyymm)>]'\
           .format(__file__)
  arguments = sys.argv
  if len(arguments) != 7:
    print(usage)
    sys.exit()

  for index in [1,3,5]:
    option = arguments[index]
    if option == '-i':
      input_filename = arguments[index+1]
    elif option == '-o':
      output_filename = arguments[index+1]
    elif option == '-d':
      period = arguments[index+1]
    else :
      print(usage)
      sys.exit()

  return {'input_filename' : input_filename,
          'output_filename' : output_filename,
          'period' : period}

def input_data(filename):

  lookup = ('utf_8','euc_jp','euc_jis_2004','euc_jisx0213',
            'shift_jis','shift_jis_2004','shift_jisx0213',
            'iso2022jp','iso2022_jp_1','iso2022_jp_2','iso2022_jp_3',
            'iso2022_jp_ext','latin_1','ascii')
  encode = None
  data_list = []

  for encoding in lookup:
    try:
      f = codecs.open(filename, 'r', encoding)
      encode = encoding
      reader = csv.reader(f)
      header = next(reader)

      for row in reader:
        date = row[0]
        user = row[2]
        lock = row[3]
        data = {'date': date, 'user': user, 'lock': lock}
        data_list.append(data)

      break
    except:
      pass
  if isinstance(encode,str):
    return data_list,encode
  else:
    raise LookupError

def data_shaping(data_list, period):
  # 2:00 -> 23:00
  date_format_list = ['%Y/%m/%d %H:%M','%Y-%m-%d %H:%M:%S']
  day_start = datetime.datetime.strptime(DAYSTART,'%H%M')
  for data in data_list:
    for date_format in date_format_list:
      try:
        date = datetime.datetime.strptime(data['date'],date_format)
        break
      except:
        pass
    data['date'] = date
    data['date'] -= datetime.timedelta(hours=day_start.hour)
    data['date'] -= datetime.timedelta(minutes=day_start.minute)

  # data mining
  period_start = datetime.datetime.strptime(period,'%Y%m')
  day_range = calendar.monthrange(period_start.year,period_start.month)[1]
  period_end = period_start + datetime.timedelta(days=day_range)
  
  mining_data = []
  user_list = []
  shaped_data = []
  for data in data_list:
    if period_start <= data['date'] and data['date'] < period_end\
      and data['lock'] in ['入室', '退室', '解錠']\
      and data['user'] != '':
      mining_data.append(data)
      if data['user'] not in user_list:
        user_list.append(data['user'])
        shaped_data.append({\
        'name': data['user'], 'timecard_data': [],\
        'writed_days':[], 'period': period})


  # data reconstruction
  for data in mining_data:
    index = user_list.index(data['user'])
    if data['lock'] == '入室':
      if data['date'].day not in shaped_data[index]['writed_days']:
        shaped_data[index]['timecard_data'].append({\
          'day': data['date'].day, 'in_time': data['date']})
        shaped_data[index]['writed_days'].append(data['date'].day)

      else:
        timecard_data_index = shaped_data[index]['writed_days'].index(data['date'].day)
        if 'in_time' not in shaped_data[index]['timecard_data'][timecard_data_index]\
          or shaped_data[index]['timecard_data'][timecard_data_index]['in_time'] \
            > data['date']:
          shaped_data[index]['timecard_data'][timecard_data_index]['in_time'] = data['date']

    elif data['lock'] == '退室':
      if data['date'].day not in shaped_data[index]['writed_days']:
        shaped_data[index]['timecard_data'].append({\
          'day': data['date'].day, 'out_time': data['date']})
        shaped_data[index]['writed_days'].append(data['date'].day)

      else:
        timecard_data_index = shaped_data[index]['writed_days'].index(data['date'].day)
        if 'out_time' not in shaped_data[index]['timecard_data'][timecard_data_index]\
          or shaped_data[index]['timecard_data'][timecard_data_index]['out_time'] \
            < data['date']:
          shaped_data[index]['timecard_data'][timecard_data_index]['out_time'] = data['date']

    elif data['lock'] == '解錠':
      if data['date'].day not in shaped_data[index]['writed_days']:
        shaped_data[index]['timecard_data'].append({\
          'day': data['date'].day, 'in_time': data['date']})
        shaped_data[index]['writed_days'].append(data['date'].day)
      else:
        timecard_data_index = shaped_data[index]['writed_days'].index(data['date'].day)
        if 'in_time' in shaped_data[index]['timecard_data'][timecard_data_index]:
          shaped_data[index]['timecard_data'][timecard_data_index]['out_time'] = data['date']

        elif 'out_time' in shaped_data[index]['timecard_data'][timecard_data_index]\
          and shaped_data[index]['timecard_data'][timecard_data_index]['out_time'] \
            < data['date']:
          shaped_data[index]['timecard_data'][timecard_data_index]['out_time'] = data['date']

  # data totalization
  for data in shaped_data:
    total_working_hours = 0
    total_working_days = 0
    
    for timecard_data in data['timecard_data']:
      if 'in_time' in timecard_data\
        and 'out_time' in timecard_data:
        diff = timecard_data['out_time'] - timecard_data['in_time']
        diff_sec = diff.seconds
        diff_min = diff_sec / 60
        diff_min = math.floor(diff_min/ROUNDDOWNTIME)*ROUNDDOWNTIME
        diff_hour = diff_min / 60

        timecard_data['working_hours'] = diff_hour
        total_working_hours += diff_hour

      else:
        timecard_data['working_hours'] = 0

      total_working_days += 1

    data['total_working_hours'] = total_working_hours
    data['total_working_days'] = total_working_days

  return shaped_data

def output_data(filename, encode, shaped_data):
  with codecs.open(filename, 'w', encode) as f:
    writer = csv.writer(f, lineterminator = os.linesep)
    for data in shaped_data:
      writer.writerow(['氏名',data['name'],'','','',''])
      writer.writerow(['集計期間',data['period'],'','','',''])
      writer.writerow(['就業日数',data['total_working_days'],'','','',''])
      writer.writerow(['就業時間',data['total_working_hours'],'','','',''])
      writer.writerow(['月日', '入室時刻', '退出時刻', '就業時間','',''])
      for timecard in data['timecard_data']:
        date_str = data['period'][0:4] + '/'\
                 + str(int(data['period'][4:6])) + '/'\
                 + str(timecard['day'])

        day_start = datetime.datetime.strptime(DAYSTART,'%H%M')
        if 'in_time' in timecard:
          # 23:00 -> 26:00
          timecard['in_time'] += datetime.timedelta(minutes=day_start.minute)
          timecard['in_time'] += datetime.timedelta(hours=day_start.hour)
          hour = timecard['in_time'].hour
          if hour < day_start.hour:
            hour += 24

          in_time_str = str(hour) + ':'\
                      + timecard['in_time'].strftime('%M')
        else:
          in_time_str = ''

        if 'out_time' in timecard:
          # 23:00 -> 26:00
          timecard['out_time'] += datetime.timedelta(minutes=day_start.minute)
          timecard['out_time'] += datetime.timedelta(hours=day_start.hour)
          hour = timecard['out_time'].hour
          if hour < day_start.hour:
            hour += 24
          out_time_str = str(timecard['out_time'].hour) + ':'\
                       + timecard['out_time'].strftime('%M')
        else:
          out_time_str = ''

        writer.writerow([\
        date_str, in_time_str, out_time_str\
        ,str(timecard['working_hours']),'',''])

      writer.writerow(['','','','','',''])

if __name__ == '__main__':
  commandline_vars = option_parser()
  data_list,encode = input_data(commandline_vars['input_filename'])
  shaped_data = data_shaping(data_list, commandline_vars['period'])
  output_data(commandline_vars['output_filename'], encode, shaped_data)



