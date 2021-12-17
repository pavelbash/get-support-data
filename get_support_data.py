#!/usr/bin/env python3.7


from netmiko import ConnectHandler, file_transfer 
import os
from argparse import ArgumentParser
from getpass import getpass
from time import strftime, sleep
from functools import wraps
from pysftp import Connection


def logger(function):
              import logging
              logging.basicConfig(filename='./log/{}.log'.format(function.__name__), level=logging.INFO)
              now = strftime("%a, %d %b %Y %H:%M:%S")
              
              @wraps(function)
              def wrapper(*args, **kwargs):
                             logging.info('{}: Ran with args: {}, and kwargs {}'.format(now, args, kwargs))
                             return function
              return wrapper


def connect(ip, login, password, case):
              with ConnectHandler(device_type='juniper_junos', host=ip, username=login, password=password, session_log='log/connection.log') as net_connect: 
                             print("-> connected to {}".format(ip)) 
                             net_connect.send_command('file archive source /var/log/* destination /var/tmp/varlog_{} compress'.format(today), expect_string=r'')
                             print('--> waiting for varlog to be created')
                             sleep(60)
                             for i in range(10):
                                           varlog_check = net_connect.send_command('file list /var/tmp/varlog_{}.tgz'.format(today), expect_string=r'')
                                           if "No such file" in varlog_check:
                                                          print("--> waiting for archive to be created...")
                                                          sleep(5)
                                                          pass
                                           else:
                                                          print("--> varlog archive created successfully")
                                                          break
                             net_connect.send_command('request support information | save /var/tmp/rsi_{}.log'.format(today), expect_string=r'')                        
                             print('--> waiting for rsi to be created')
                            sleep(60)
                             for i in range(5):
                                           rsi_check = net_connect.send_command('file list /var/tmp/rsi_{}.log'.format(today), expect_string=r'')
                                           if "No such file" in rsi_check:
                                                          print("--> waiting for rsi log file to be created...")
                                                          sleep(5)
                                                          pass
                                           else:
                                                          print("--> rsi log file created successfully")
                                                          break

                             path = os.getcwd()
                             if case in os.listdir(path):
                                           print(os.listdir(path), '\n###directory exists###')
                             else:
                                           os.mkdir(case)
                                           file_transfer(net_connect,source_file='rsi_{}.log'.format(today),dest_file='./{}/rsi_{}.log'.format(case,today),direction='get',overwrite_file=True)
                                           file_transfer(net_connect,source_file='varlog_{}.tgz'.format(today),dest_file='./{}/varlog_{}.tgz'.format(case,today),direction='get',overwrite_file=True)


def upload_to_lfs1(login, password, case, case_description):
              with ConnectHandler(device_type='linux', host='lfs1.vzbi.com', username=login, password=password) as connect:
                             print('-> connected to lfs1.vzbi.com')
                             # checking if directory for case already exists of lfs1 and creating new one if it does not
                             dir_check = connect.send_command('ls /tftpboot/files/lab/cases/juniper/ | grep {}'.format(case))
                             if dir_check == None:
                                           workdir = '/tftpboot/files/lab/cases/juniper/' + case + '_' + case_descripption
                                           connect.send_command('mkdir {}'.format(workdir))
                                           print('--> directory {} created on lfs1.vzbi.com'.format(workdir))
                             else:
                                           workdir = '/tftpboot/files/lab/cases/juniper/' + dir_check
                                           print('--> directory {} exists on lfs1.vzbi.com, using existing directory'.format(workdir))

                            file_transfer(connect,source_file='./{}/varlog_{}.tgz'.format(case,today),dest_file='varlog_{}.tgz'.format(today),direction='put',overwrite_file=True, file_system=workdir)     
                             print('--> varlog uploaded to lfs1.vzbi.com:{}'.format(workdir))
                            file_transfer(connect,source_file='./{}/rsi_{}.log'.format(case,today),dest_file='rsi_{}.log'.format(today),direction='put',overwrite_file=True, file_system=workdir)     
                             print('--> rsi uploaded to lfs1.vzbi.com:{}'.format(workdir))
                             connect.send_command('chmod -R 766 {}'.format(workdir))


def upload_to_juniper(case):
              with Connection('sftp.juniper.net', username='Anonymous', password='Anonymous') as sftp:
                             print('-> connected to sftp.juniper.net')
                             with sftp.cd('pub/incoming/{}'.format(case)):
                                           sftp.put('./{}/varlog_{}.tgz'.format(case,today))
                                           print('--> varlog uploaded to sftp.juniper.net:/pub/incoming/{}'.format(case))
                                           sftp.put('./{}/rsi_{}.log'.format(case,today))
                                           print('--> rsi uploaded to sftp.juniper.net:/pub/incoming/{}'.format(case))


def cleanup(case):
              print('cleaning up directories')
              os.remove('./{}/rsi_{}.log'.format(case,today))
              os.remove('./{}/varlog_{}.tgz'.format(case,today))
              os.rmdir('./{}'.format(case))


def main():
              parser = ArgumentParser()
              parser.add_argument('-l', '--LOGIN', type=str, help='login name to connect to device', required=True)
              parser.add_argument('-d', '--DEVICE', type=str, help='ip address to connect to device', required=True)
              parser.add_argument('-c', '--CASE', type=str, help='JTAC case number', required=True)
              args = parser.parse_args()
              login = args.LOGIN
              ip = args.DEVICE
              case = args.CASE
              case_description = input('Please provide case description, not whitespaces allowed: ')
              case_description = case_description.strip() 
              password = getpass("Please enter your password:")

              global today
              today = strftime("%Y-%m%d") 
              try:
                             connect(ip, login, password, case)
              except Exception as err:
                             print(err)

              try:
                             upload_to_lfs1(login, password, case, case_description)
              except Exception as err:
                             print(err)

#            try:
#                           upload_to_juniper(case)
#            except Exception as err:
#                           print(err)

              try:
                             cleanup(case)
              except Exception as err:
                             print(err)


if __name__ == '__main__':
        main()
