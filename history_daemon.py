#!/usr/bin/python2.7
import os
import sys

include_path = os.path.abspath(os.path.join(__file__, os.pardir))
sys.path.insert(0, include_path)


import time
import requests
import simplejson
import json
import datetime
import email

import bitcoinaverage as ba
from bitcoinaverage.config import HISTORY_QUERY_FREQUENCY, CURRENCY_LIST
from bitcoinaverage.helpers import write_log
from bitcoinaverage import history_writers


if ba.server.PROJECT_PATH == '':
    ba.server.PROJECT_PATH = include_path
if ba.server.LOG_PATH == '':
    ba.server.LOG_PATH = os.path.join(ba.server.PROJECT_PATH, 'runtime', 'app.log')
if ba.server.HISTORY_DOCUMENT_ROOT == '':
    ba.server.HISTORY_DOCUMENT_ROOT = os.path.join(ba.server.PROJECT_PATH, 'api', 'history')

write_log('script started', 'LOG')


while True:
    ticker_url     = ba.server.API_INDEX_URL+'all'
    fiat_data_url  = ba.server.API_FIAT_DATA_URL
    try:
        current_data_all = requests.get(ticker_url, headers=ba.config.API_REQUEST_HEADERS).json()
        fiat_data_all    = requests.get(fiat_data_url, headers=ba.config.API_REQUEST_HEADERS).json()
    except (simplejson.decoder.JSONDecodeError, requests.exceptions.ConnectionError):
        time.sleep(2)
        continue

    current_data_datetime = current_data_all['timestamp']
    current_data_datetime = current_data_datetime[:-6] #prior to python 3.2 strptime doesnt work properly with numeric timezone offsets.
    current_data_datetime = datetime.datetime.strptime(current_data_datetime, '%a, %d %b %Y %H:%M:%S')
    current_data_timestamp = int((current_data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())

    #do we need to check and create folder only when history demon started firstly?
    actual_currency_list = {}

    for currency_code in current_data_all:
        if currency_code in CURRENCY_LIST:
            actual_currency_list[currency_code] = current_data_all[currency_code]; # add currency code if it's represent in CURRENCY LIST
            if not os.path.exists(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code)):
                os.makedirs(os.path.join(ba.server.HISTORY_DOCUMENT_ROOT, currency_code))


    for currency_code in actual_currency_list:
        history_writers.write_24h_csv(currency_code, actual_currency_list[currency_code]['averages'], current_data_timestamp)
        history_writers.write_1mon_csv(currency_code, current_data_timestamp)
        history_writers.write_forever_csv(currency_code, actual_currency_list[currency_code]['averages']['total_vol'], current_data_timestamp)
        history_writers.write_volumes_csv(currency_code, actual_currency_list[currency_code], current_data_timestamp)

        #write global average 24th sliding window
        history_writers.write_24h_global_average(fiat_data_all, actual_currency_list,  currency_code, current_data_timestamp)


    current_time = time.time()
    timestamp = email.utils.formatdate(current_time)
    sleep_time = HISTORY_QUERY_FREQUENCY - (current_time % HISTORY_QUERY_FREQUENCY)
    sleep_time = min(HISTORY_QUERY_FREQUENCY, sleep_time)

    print '%s, sleeping %ss - history daemon' % (timestamp, str(sleep_time))

    time.sleep(sleep_time)


