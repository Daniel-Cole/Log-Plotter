from datetime import datetime, timedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from graphs import create_graph


def index(request):
	return render(request, 'dashboard.html', {'available_graphs': create_graph.get_available_graphs()})

@csrf_exempt
def getGraphGroupBy(request, graph):
	start_date = request.GET.get('start_date')
	end_date = request.GET.get('end_date')
	groupby = request.GET.get('groupby')

	if(groupby == "null"):
		groupby = "hour"
		print('resetting groupby')
	else:
		groupby = groupby.lower()
	if(start_date != "null"):
		start_date_fmt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
	else:
		start_date = None
		start_date_fmt = None

	if(end_date != "null"):
		end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
	else: 
		end_date=None
		end_date_fmt = None

	if(end_date_fmt is None and start_date_fmt is None):
		start_date = datetime.strftime((datetime.now()-timedelta(days=7)),'%Y-%m-%d %H:%M:%S') 
		end_date = datetime.strftime((datetime.now()),'%Y-%m-%d %H:%M:%S') 

	plotted_graph = create_graph.find_graph(graph, start_date_fmt, end_date_fmt, groupby)
	return render(request, 'graph.html', {'title': graph, 'graph': plotted_graph['graph'], 'graph_info': plotted_graph['info'], 'groupby' : plotted_graph['group_by'], 'start_date': start_date, 'end_date': end_date})

@csrf_exempt
def getGraph(request, graph):

	start_date = request.GET.get('start_date')
	end_date = request.GET.get('end_date')

	if(start_date != "null"):
		start_date_fmt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
	else:
		start_date = None
		start_date_fmt = None

	if(end_date != "null"):
		end_date_fmt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
	else: 
		end_date=None
		end_date_fmt = None

	#start/end_date_fmt is needed as arg None for plotted graph isn't going to work - put this in create_graph()
	#none specified so...
	if(end_date_fmt is None and start_date_fmt is None):
		print('none specified...')
		start_date = datetime.strftime((datetime.now()-timedelta(days=7)),'%Y-%m-%d %H:%M:%S') 
		end_date = datetime.strftime((datetime.now()),'%Y-%m-%d %H:%M:%S') 

	plotted_graph = []
	try:
		plotted_graph = create_graph.find_graph(graph, start_date_fmt, end_date_fmt, None)
	except Exception as e:
		print('returning bad response')
		print(str(e))
		return HttpResponse("Unable to create graph: {0}".format(str(e)),status=400)

	return render(request, 'graph.html', {'title': graph, 'graph': plotted_graph['graph'], 'graph_info': plotted_graph['info'], 'start_date': start_date, 'end_date': end_date})
	


