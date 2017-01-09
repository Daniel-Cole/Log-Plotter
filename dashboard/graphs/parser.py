import ast
from datetime import datetime, timedelta
import operator
import os
import re
import time
import config

#TODO: 
#refactor functions into distinct files

ops = { "+": operator.add, "-": operator.sub, "*": operator.mul, '/': operator.div }

def set_date_range(start_date, end_date):
	""" 
	This method is used to check the date range and if a particular date
	isn't specified, it will generate a start/end date
	"""
	#if both dates specified - do nothing
	if end_date and start_date:
		if(end_date < start_date):
			raise Exception('end date must not be before start state')
		return [start_date, end_date]

	#if start_date is specified then we will go until current day
	if start_date and not end_date:
		end_date = datetime.now()
		return [start_date, end_date]

	#if end date specified but not start date then get 7 day lead up to specified end date
	if end_date and start_date is None:
		start_date = (end_date - timedelta(days=7))
		return [start_date, end_date]

	#if no start date specified then we will just go back 7 days
	end_date = datetime.now()
	start_date = (end_date - timedelta(days=7))
	return [start_date, end_date]

#the file to read from, the data array to return
#date not always required, only if missing date as some logs don't have it
#e.g no YYYYMMDD specified, but has TIME
def read_file_time_series(file, regex, data, date):
	try: 
		with open(file) as log_file:
			content = log_file.readlines()
			for line in content:
				val = re.match(regex,line)
				if(val):
					values = val.groups(0)
					vals_to_add = [(date+values[0])]
					itervals = iter(values)
					next(itervals)
					for value in itervals:
						#append date to time if missing
						vals_to_add.append(value)
					data.append((tuple(vals_to_add)))
	except IOError as e: 
		print('file doesn\'t exist: ' + str(e))
	return data


#specifically for errors by day - should be able to strip code duplication
def summarise_by_hour(data, date_stamp):
	summarised_data = []

	#unique list of urls
	unique_urls = []

	for value in data:
		unique_urls.append(value[1])
	unique_urls = set(unique_urls)

	for url in unique_urls:
		for i in range(0,24): #loop over each hour
			if(re.match(r'(^\b\d\b.*$)',str(i))):
				hr = "0"+str(i)
			else:
				hr = i
			count = sum(1 for value in data if re.match(r'^.*\d{4,4}-\d{2,2}-\d{2,2} %s:.*$' % hr, value[0]) and value[1] == url)
			val = tuple((str(date_stamp)+" "+str(hr)+":00:00", url, count))
			summarised_data.append(val)
	#finally! hr, url, count
	return summarised_data

#grep -A20 '\[ERROR\].*JAXRS operation failed invoking direct' logfile | grep 'CamelHttpPath' | sed -e 's/^.*CamelHttpPath=\(.*\), CamelRedelivered=.*/\1/'
def parse_mymsd_backend_errors(start, end):
	regex = r'^.*\[ERROR\] (\d.*),\d{3,3}.*JAXRS operation failed invoking direct.*$' #first regex is to find the error (excludes error)
	regex_error_url = r'^.*CamelHttpPath=(.*), CamelRedelivered.*$' #second regex is URL

	date_range = set_date_range(start, end) #default is 7 days of data from today
	current_date = date_range[0]
	end_date = date_range[1]

	#need to check for current day as log format is different
	today_date = datetime.strftime(datetime.now(),'%Y-%m-%d');

	summarised_data = []
	while current_date <= end_date:
		date_str = str(current_date)[:10] #get date for log files - myMSD.log
		#read files and check for today
		if(date_str == today_date):
			current_file = os.path.join(config.mymsd_log_location,config.mymsd_name_format).replace('-','') #perform replace after comparison to today
		else:
			current_file = os.path.join(config.mymsd_log_location,config.mymsd_name_format+"."+date_str).replace('-','')
		try: 
			data = [] #all the data to return
			with open(current_file) as log_file:
				content = iter(log_file.readlines()) #need to create iteratable so that we can skip over lines as needed
				for line in content:
					#first match will give time
					#second match will give the URL
					val = re.match(regex,line)
					if(val):
						date_time = val.groups(0)[0]
						#val_two is our line with the URL
						val_two = re.match(regex_error_url,next(content))
						i = 0
						while not val_two: #need to get the URL for the error, it's 20 lines down or so
							i += 1
							if(i==100):
								#make sure we don't get stuck in loop
								raise Exception('Expected URL to be logged with error')
							val_two = re.match(regex_error_url,next(content))
						error_url = val_two.groups(0)[0]
						data.append(tuple((date_time,error_url)))
			summarised_data += summarise_by_hour(data,date_str)
		except IOError as e:
			print('file doesn\'t exist: ' + str(e)) #file skipped as doesn't exist
		current_date = (current_date + timedelta(days=1)) #increment date for next file
	return summarised_data

#data should be a list of tuples where the first value is the date
def group_by(data, freq):
	#where freq = 'hour', 'minute'
	if(freq == 'hour'):
		factor = [1, 24, 1]
		return map_values(factor, data)

	if(freq == 'minute'):
		factor = [2, 1440, 60, 1]
		return map_values(factor, data)

	if(freq == 'second'):
		#1 day worth of seconds
		factor = [3, 86400, 3600, 60, 1]
		return map_values(factor, data)

	raise ValueError('Group by frequency must be one of hour, minute or second')

#first value is the number of times we need, i.e 2 = hour, then minute, then second 
def map_values(factor, data):
	grouped_data = {}

	if(len(data[0][0]) == 13): #if only time is provided
		time_start = 0
	else:
		time_start = 11 #where the first time val is (i.e hr)

	time_step = 3 #moving along to next hr/min/sec
	time_diff = 2 #number of characters in time val (hr = 23, min = 50)
	offset = 2 #offset for first 2 values in array

	#set up points in time for storing the values
	for point in range(factor[1]):
		grouped_data[point] = []

	#now we can loop over data
	for values in data:
		interval_point = 0
		for f in range(factor[0]):
			#the start of the time value, i.e hour, 
			time_idx = time_start + (time_step*f)
			val_contrib = int(values[0][time_idx:(time_idx+time_diff)])*factor[f+offset] #offset needed to move through array
			interval_point += val_contrib
		grouped_data[interval_point].append(values) #interval point is the time
	return grouped_data

#date is required 
#frequency is for hours or minutes
def convert_from_timestamp(date, freq, timestamp):
	#do nothing if frequency second
	factor = -1
	if(freq == 'hour'):
		factor = 3600
		hr = timestamp
	
	if(freq == 'minute'):
		factor = 60
		hr = timestamp // 60 

	if(freq == 'second'):
		factor = 1
		hr = timestamp // 3600 

	if(freq == 'ms_1000'):
		factor = 1

	if(freq == 'ms_100'):
		factor = 10

	if(freq == 'ms_10'):
		factor = 100

	if(freq == 'ms_1'):
		factor = 1000

	if factor == -1:
		raise ValueError('converting from timestamp only supported for hour, minute or second')
	date_from_timestamp = ""
	if(freq[0:2] == 'ms'):
		date_from_timestamp = str(datetime.fromtimestamp(timestamp/factor).strftime('%Y-%m-%d %H:%M:%S.%f'))
	else:
		date_from_timestamp = str(datetime.fromtimestamp(timestamp*factor).strftime('%Y-%m-%d %H:%M:%S.%f'))
	try:
		return (date[0:10]+' ' +str(hr)+str(date_from_timestamp)[13:19])
	except: 
		return (date[0:10]+' ' +date[11:13]+str(date_from_timestamp)[13:19]) #this happens for concurrent connections
	
	

#data must be provided in 1 hour blocks
def count_concurrent_connections(data, date, groupby, accuracy):
	#we want to store the 5 minute block, and the connections in that interval
	#we need somewhere to put the block data {}, data[x] is block 00:00:00 - 00:00:05 and the corresponding values is a list of tuples, with 
	#interval point and number of concurrent connections
	if(len(data) == 0):
		return [None]

	concurrent_connections = {}
	#connections that end after 1 hour are going to loop around FIX 
	factor_vals = {'ms_1': [3600000, 60000, 1000, 100, 10, 1], 'ms_10': [360000, 6000, 100, 10, 1, 0], 'ms_100' : [360000, 600, 10, 1, 0, 0], 'ms_1000' : [36000, 60, 1, 0, 0, 0]}
	factor = ""
	if(accuracy == None):
		factor = 'ms_100'
	else:
		factor = accuracy

	for x in range(0, factor_vals[factor][0]):
		concurrent_connections[x] = 0

	for value in data:
		#NEED TO LOOP OVER EVERY SECOND THAT IT IS ACTIVE FOR 
		start_time = datetime.strptime(value[0],"%H:%M:%S.%f").time()
		end_time = datetime.strptime(value[1],"%H:%M:%S.%f").time()
		#need min, second, ms
		start_minute_point = int(str(start_time)[3:5])*factor_vals[factor][1]
		start_second_point = int(str(start_time)[6:8])*factor_vals[factor][2]
		start_100_ms_point = int(str(start_time)[9:10])*factor_vals[factor][3]
		start_10_ms_point = int(str(start_time)[10:11])*factor_vals[factor][4]
		start_1_ms_point = int(str(start_time)[11:12])*factor_vals[factor][5]

		start_interval_point = start_minute_point+start_second_point+start_100_ms_point+start_10_ms_point+start_1_ms_point

		end_minute_point = int(str(end_time)[3:5])*factor_vals[factor][1]
		end_second_point = int(str(end_time)[6:8])*factor_vals[factor][2]
		end_100_ms_point = int(str(end_time)[9:10])*factor_vals[factor][3]
		end_10_ms_point = int(str(end_time)[10:11])*factor_vals[factor][4]
		end_1_ms_point = int(str(end_time)[11:12])*factor_vals[factor][5]

		end_interval_point = end_minute_point+end_second_point+end_100_ms_point+end_10_ms_point+end_1_ms_point

		while start_interval_point <= end_interval_point:
			concurrent_connections[start_interval_point] += 1
			start_interval_point += 1
	
	conns = []

	#this will return all of our concurrent connections at the particular times
	for timestamp in range(0, factor_vals[factor][0]):
		if(concurrent_connections[timestamp] > 0):
			interval_time = convert_from_timestamp(date, factor, timestamp)
			conns.append(tuple((interval_time,concurrent_connections[timestamp])))

	#let's find the maximum values according to the groupby
	conns = group_by(conns, groupby)

	conn_max_per_interval = {}

	### finding each maximum connection in an interval
	### second interval means 60 
	for key in conns:
		current_max_val = 0
		for value in conns[key]:
			current_conn_count = int(value[1])
			if(current_conn_count > current_max_val):
				current_max_val = current_conn_count
		conn_max_per_interval[key] = current_max_val #store the maximum value found, i.e hour or minute
	

	#bit of a pain to convert back from unix timestamp to correct day. but worth tradeoff for speed
	data = []
	for key in conn_max_per_interval:
		if(conn_max_per_interval[key] > 0):
			time = convert_from_timestamp(date, groupby, key)
			connections = conn_max_per_interval[key]
			data.append(tuple((time, connections)))
	return data

#get the hour range that the user has specified
def get_hours(start, end):
	hours = []
	while(start.hour < end.hour):
		hours.append(start.hour)
		start = (start + timedelta(hours=1))
	hours.append(end.hour) #include end hour no matter what
	return hours


#groupby = minute/second, accuracy = 0.001s, 0.01s, 0.1s, 1s
def parse_concurrent_connections(start, end, groupby, accuracy):
	#need to loop over each file
	date_range = set_date_range(start, end) #default is 7 days of data from today
	current_date = date_range[0]
	end_date = date_range[1]
	
	#get date, start and end time from log entry
	regex = r'^.*(\d{4,4}-.*)T(\d.*)\+.*T(\d.*)\+.*$'

	#our connections that we want to return
	concurrent_connections = []

	hours = get_hours(start, end) #the hours that we want
	files = get_log_files(start, end, 'service_perf')

	for file in files:
		data = [] #we want a block of data for each day
		try:
			with open(file) as log_file:
				content = log_file.readlines()
				for line in content:
					values = re.match(regex,line)
					if(values): #maybe remove this later by stripping first and last line??
						vals = values.groups()
						#datetime removes millseconds if it's all zeros - this isn't good for a generic format
						#add 1 to the end to prevent 
						start_time = vals[1]+"1"
						end_time = vals[2]+"1"
						data.append(tuple((start_time, end_time)))
				#now it's all grouped by the hour
				grouped_values = group_by(data, 'hour') #counting connections in hour blocks hence hour
				#slap everything back into a list, 0 = time, 1 = num connections
				for time in range(0, 24):
				#need to make sure we pass through hour with date
				#date must include correct hour
					if(re.match(r'(^\b\d\b.*$)',str(time))):
						hr = "0"+str(time)
					else:
						hr = time
					if(not time in hours): #check if we're looking for this hour
						continue
					date_hr = str(current_date)[:10] + ' ' + str(hr) + str(current_date)[-6:]
					for val in count_concurrent_connections(grouped_values[time], date_hr, groupby, accuracy):
						if(val): #null check
							concurrent_connections.append(val) #add the value to our overall list of concurrent connections
		except IOError as e:
			print('file doesn\'t exist: ' + str(e))
		current_date = (current_date + timedelta(days=1)) #increment date for next file
			
	return concurrent_connections

"""
This function will find all of the log files to be retrieved
"""
def get_log_files(start, end, log_file):
	if(not log_file in config.log_files):
		raise ValueError("Log file must be one of {0}".format(config.log_files.keys()))

	#load in specific details for this particular log file
	log_file_location = config.log_files[log_file]['log_location']
	log_file_seperator = config.log_files[log_file]['date_seperator']
	log_file_current_day_diff = config.log_files[log_file]['current_day_diff']
	log_file_date_fmt = config.log_files[log_file]['date_fmt']
	log_file_increment = config.log_files[log_file]['file_increment']
	log_file_postfix = config.log_files[log_file]['postfix']

	current_date_time = datetime.now()
	
	#log files to return
	files = []

	#today is one of our log files so add it to our list of log files
	#note that it's assumed the current day is just the file name
	if(log_file_current_day_diff and current_date_time >= start and current_date_time <= end):
		files.append(os.path.join(log_file_location,log_file))

	current_date = start
	while current_date <= end:
		#need to check for each individual log file
		date_str = datetime.strftime(current_date,log_file_date_fmt) #get date for log files
		files.append(os.path.join(log_file_location,log_file+log_file_seperator+date_str)+log_file_postfix)
		current_date = (current_date + timedelta(**log_file_increment)) #increment current date to get next file
	return files

"""
used to parse simple data with an x and y value
"""
def parse_basic(files, start, end, log_file, regex, groupby, agg):
	#loop over files are parse the data with the given regex
	data = []
	for file in files:
		try: 
			with open(file) as log:
				content = log.readlines() #need to create iteratable so that we can skip over lines as needed
				for line in content:
					values = re.match(regex,line)
					if(values): #we have a match
						vals = values.groups()
						check_date = datetime.strptime(vals[0], config.log_files[log_file]['log_date_fmt']) #check here for if value falls in the time
						if(check_date < start or check_date > end):
							continue #skip if this falls out of the range
						data.append(tuple((datetime.strftime(check_date, "%Y-%m-%d %H:%M:%S"), vals[1])))
		except IOError as e:
			print('file doesn\'t exist: ' + str(e)) #file skipped as doesn't exist
	#after the data has been parsed we want to group it all
	return data


"""
attempt to parse logs with dynamic regex
1) start 
2) end 
3) regex to match -- if first match is not date then xsrc={x} must be specified, where x is the match
4) groupby -- how do you want to group this data?, how minute etc
5) second groupby field?

args = {
	"trace": 0,
	"xsrc": 1, 
	"ysrc": 2, | "ysrc" = 3-4 | 1*2 | 
	"groupby": "minute"
	"agg": "sum"
}
xsrc should always be a date
where groupby is hour, minute, second
where agg can be 1 of sum, average, count

{'trace': 2, 'xsrc': 0, 'ysrc': '1-2', 'groupby': 'minute', 'agg':'avg', 'graphtype' : 'scatter|line'}

trace will define the categories
"""
def parse_data(start, end, regex, args, log_file):
	date_range = set_date_range(start, end) #get the dates
	
	files = get_log_files(start,end,log_file) #get the files to go over
	
	regex = r"^.*" + regex + r"$"

	if(len(args) > 1):
		args = ast.literal_eval(args)
		trace = int(args['trace']) #must be int as referencing a capture group 
		xsrc = int(args['xsrc'])
		ysrc = args['ysrc']
		ytype = args['ytype']
		groupby = args['groupby']
		agg = args['agg']

		#trace exists
		if(trace):
			return parse_trace(files, start, end, regex, trace, xsrc, ysrc, ytype, groupby, agg)
		return parse_basic(regex, groupby, agg) #add more arguments in here

	return parse_basic(files, start, end, log_file, regex, '', '') #no args specified so assume x = first capture, y = second capture


"""
used if the user needs to do some arithmetic with the value
"""
def calc_ysrc(ysrc, values):
	#check for arithmetic on ysrc
	if(len(ysrc) > 1): #first attempt to parse with int, if that doesnt work, then try to parse date
		try: 
			val_one = values[int(ysrc[0])] #first argument, e.g start time
			operator = ysrc[1] 
			val_two = values[int(ysrc[2])] #second argument e.g end time
			return ops[operator](int(val_one),int(val_two)) # prints 2
		except (ValueError, TypeError) : #user hasn't specified int, so must be date?
			try:
				val_one = datetime.strptime(values[int(ysrc[0])], '%H:%M:%S.%f')
				operator = ysrc[1]
				val_two = datetime.strptime(values[int(ysrc[2])], '%H:%M:%S.%f')
				return ops[operator](val_one,val_two)
			except ValueError:
				raise ValueError("ysrc values must be either integers or dates")
	return values[ysrc] #if only 1 value just return


"""
used to parse more complicated data with more than 1 trace
e.g. service performance call times, datetime, start, end,
traceidx = 
"""
def parse_trace(files, start, end, regex, trace_idx, xsrc, ysrc, ytype, groupby, agg):
	traces = {}
	for file in files:
		try: 
			current_date = ""
			with open(file) as log_file:
				content = log_file.readlines() #need to create iteratable so that we can skip over lines as needed
				for line in content:
					values = re.match(regex,line)
					if(values): #we have a match
						vals = values.groups()
						current_date = vals[xsrc].replace('T',' ') #hack as some capture times have a T instead of space

						check_date = datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S.%f') #check here for if value falls in the time

						if(check_date < start or check_date > end):
							continue #skip if this falls out of the range

						key = vals[trace_idx] #get the trace key to see where we are going to put this particular value
						if(key in traces):
							traces[key].append(tuple((current_date, calc_ysrc(ysrc, vals)))) #add to existing list of values for this key
						else:
							traces[key] = [tuple((current_date, calc_ysrc(ysrc, vals)))] #create a new list for this new key

				#now we need to group by if specified exists
				# we should only have x and y values now for each trace
				if(groupby):
					for key in traces: #loop over each key
						traces[key] = group_by(traces[key], groupby) #re-allocate data into grouped blocks
						for time in traces[key]: 
							seconds = [] #this should be every second in the time
							if(ytype == 'time'):
								if(traces[key][time]): #if time has a value
									for val in traces[key][time]:
										seconds.append(float(val[1].total_seconds())) #add all the seconds in this interval 
									traces[key][time] = sum(seconds)/len(seconds) #should check here to see what the user actually wants to do

					for key, value in traces.items(): #convert time back to something plotly can read
						traces[key] = []
						for time, values in value.items():
							traces[key].append(tuple((convert_from_timestamp(current_date, groupby, time), values)))
		except IOError as e:
			print('file doesn\'t exist: ' + str(e)) #file skipped as doesn't exist
	#before we return we need to make sure that each trace has 
	return traces

def parse_mymsdpweb_letter_size(start, end):
	#regex to grab time and size
	regex = "\[(.*\d{4,4}:\d{2,2}:\d{2,2}:\d{2,2}).*/letters/[0-9]+.*HTTP.*\" (\d.*)"
	return parse_data(start, end, regex, '', 'ssl_request_log')