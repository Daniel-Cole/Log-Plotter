ssl_log_location="D:\logs\ssl_logs"
ssl_name_format="ssl_request_log"
ssl_postfix=".log"

mymsd_log_location="D:\logs\mymsd_logs"
mymsd_name_format="myMSD.log"

service_perf_location="D:\logs\service"
service_perf_format="service_perf"

#all the possible log files supported by this application
#current day different is if log format changes for past days
#postfix is for anything at the end of the log file
#increment is how often a log file is created
seperator_idx = 1
log_files = {mymsd_name_format : {'log_location' : mymsd_log_location, 'date_seperator' : '.', 'current_day_diff' : True, 'date_fmt':'%Y%m%d', 'file_increment' :{"days" : 1}, 'postfix': '', 'log_date_fmt': '%Y-%m-%d %H:%M:%S'}, service_perf_format : {'log_location' : service_perf_location, 'date_seperator' : '.', 'current_day_diff' : False, 'date_fmt':'%Y%m%d', 'file_increment' :{"days" : 1}, 'postfix' : '', 'log_date_fmt' : '%Y-%m-%d %H:%M:%S'}, ssl_name_format : {'log_location' : ssl_log_location, 'date_seperator' : '.', 'current_day_diff' : False, 'date_fmt':'%Y%m%d%H'+'00', 'file_increment' : {"hours" : 1}, 'postfix' : ssl_postfix, 'log_date_fmt':'%d/%b/%Y:%H:%M:%S'}}

