import re
from datetime import timedelta
import plotly
from plotly.graph_objs import Scatter, Layout
import numpy as np
import parser


# each graph will return a div which can be inserted into the page
available_graphs = {'Service Performance' : 'Service Performance', 'Letters' : ['Outgoing Letter Size', 'Letter Views Per Client'], 'Errors' : ['Datapower 500s'], 'Client Lockouts' : ['10 Minute Lockouts', '24 Hour Lockouts'], 'Throttle': ['Connections Per Minute', 'Concurrent Connections']}

# need to check for last update time, so that we only update when forced or if doesn't exist
def find_graph(graph, start_date, end_date, groupby):
	if graph == 'Concurrent Connections':
		return plot_concurrent_connections(start_date, end_date, groupby)
	if graph == "Outgoing Letter Size":
		return plot_mymsdpweb_letter_size(start_date, end_date)
	if graph == "Datapower 500s":
		return plot_mymsd_log_errors(start_date, end_date)
	if graph == "Service Performance":
		return plot_service_perf(start_date, end_date, groupby)
	if graph == "Letter Views Per Client":
		return plot_letters_viewed(start_date, end_date)

def plot_letters_viewed(start_date, end_date):
	return

def plot_mymsdpweb_letter_size(start_date, end_date):
	values = parser.parse_mymsdpweb_letter_size(start_date, end_date)
	if(not values or len(values) == 0):
		raise ValueError('No data found for date range')
	graph = {}
	# we want to calculate average, 90th percentile, and maximum here
	x = []
	y = []

	for val in values:
		x.append(val[0])
		y.append(int(val[1]))  # need to append int for df


	total = sum(y)
	average = total / len(y)
	percentile = np.percentile(y, 90)

	# add particular graph information
	graph['info'] = "Total bytes sent for period: {0}\nAverage bytes sent per letter: {1}\n90th percentile: {2}\n".format(total, average, percentile)

	trace = Scatter(x=x, y=y, mode='markers')
	data = [trace]
	layout = generate_layout("Outgoing Letter Size", "Date", "Letter Size(Bytes)")

	graph['graph'] = (plotly.offline.plot({
		"data": data,
		"layout": layout 
	}, show_link=False, include_plotlyjs=False, output_type='div'))
	return graph


def plot_mymsd_log_errors(start_date, end_date):
	values = parser.parse_mymsd_backend_errors(start_date, end_date)

	graph = {}
	
	graph['info'] = 'Datapower Errors'

	urls = []
	for value in values:
		urls.append(value[1])
	unique_urls = set(urls)

	data = []
	traces = {}

	for url in urls:  # group by endpoint
		x = []
		y = []
		for value in values:
			if(value[1] == url):
				x.append(value[0])  # time
				y.append(value[2])  # count
		trace = Scatter(x=x, y=y, name=url)
		traces[url] = trace

	for trace in traces.values():
		data.append(trace)

	# plot graph
	graph['graph'] = (plotly.offline.plot({
		"data": data,
		"layout": generate_layout("myMSD.log errors", "Date", "Frequency")
	}, show_link=False, include_plotlyjs=False, output_type='div'))
	return graph

def plot_service_perf(start_date, end_date, groupby):
	print('grpby:')
	print(groupby)
	values = parser.parse_data(start_date, end_date, '(\d{4,4}-.*T(\d.*))\+.*T(\d.*)\+.*(/rest/.*)\".*', ("{'trace': 3, 'xsrc': 0, 'ysrc': '2-1', 'ytype': 'time', 'groupby': '%s', 'agg':'avg'}" % groupby), 'service_perf')

	name_regex = r'^.*/(.*)$'

	data = []
	traces = {}
	averages = {}
	for value in values:  # each url
		x = []
		y = []
		total_sum = 0
		counter = 0
		for val in values[value]:
			x.append(val[0])  # time
			y.append(val[1])  # count
			if(type(val[1]) is float and val[1] > 0):
				total_sum += val[1]
				counter += 1
		averages[value] = total_sum / counter
		trace = Scatter(x=x, y=y, name=value, text=re.match(name_regex, value).group(1))
		traces[value] = trace

	for trace in traces.values():
		data.append(trace)

	graph = {}

	graph['info'] = 'Averages:\n' 
	print(averages)
	averages = sorted(averages.items(), key=lambda x: x[1], reverse=True) 
	for average in averages:
		graph['info'] += "{0}: {1:2.3f}\n".format(average[0], average[1]) 


	graph['group_by'] = ['Hour', 'Minute']
	
	# plot graph
	graph['graph'] = (plotly.offline.plot({
		"data": data,
		"layout": generate_layout("MyMSD -> Datapower API calls", "Date/Time", "Frequency")
	}, show_link=False, include_plotlyjs=False, output_type='div'))
	return graph

def plot_concurrent_connections(start_date, end_date, groupby):
	graph = {}
	
	graph['group_by'] = ['Hour', 'Minute', 'Second']

	values = parser.parse_concurrent_connections(start_date, end_date, groupby, 'ms_10')
	x = {}
	y = {}
	current_date = start_date
	while current_date <= end_date:
		x[str(current_date)[0:10]] = []
		y[str(current_date)[0:10]] = []
		current_date = (current_date + timedelta(days=1))  # increment date for next file

	max_num = 0
	for value in values:
		x[value[0][0:10]].append(value[0])
		y[value[0][0:10]].append(value[1])
		if(value[1] > max_num):
			max_num = value[1]

	traces = {}
	for key in x:
		if(len(x[key]) > 0):
			traces[key] = Scatter(x=x[key], y=y[key], name=key)

	data = []
	for trace in traces.values():
		data.append(trace)

	graph['info'] = "Maximum number of concurrent connections observed: {0}".format(max_num)

	layout = Layout(title="Concurrent Connections", width="95%")
	graph['graph'] = (plotly.offline.plot({
		"data": data,
		"layout": layout 
	}, show_link=False, include_plotlyjs=False, output_type='div'))
	return graph


def get_available_graphs():
	return available_graphs

def generate_layout(title, xaxis_title, yaxis_title):
	layout = Layout(
		title=title,
		width="95%",
		xaxis=dict(
			title=xaxis_title,
			titlefont=dict(
			family='Courier New, monospace',
			size=18,
			color='#7f7f7f'
			)
			),
		yaxis=dict(
			title=yaxis_title,
			titlefont=dict(
				family='Courier New, monospace',
				size=18,
				color='#7f7f7f'
				)
			)
		)
	return layout
