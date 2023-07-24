import os 
import json
import argparse
import numpy as np
from glob import glob
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from matplotlib.lines import Line2D
from matplotlib.widgets import CheckButtons
from matplotlib import gridspec
from matplotlib import colormaps as cm

# REQUIRES MATPLOTLIB 3.7.X !!!!
# add option to plot from cmd only providing dir.

def file_reader(path):

	'''Reads in a TRIOS output file for an SDT measurement from a path and returns the contained data as a dict.'''

	with open(path,'r',encoding='utf8') as inf:
		raw = inf.read()

	data = {}

	indices_open = []
	indices_close = []

	for i,char in enumerate(raw):
		if char == '[':
			indices_open.append(i)
		elif char == ']':
			indices_close.append(i)

	assert len(indices_open) == len(indices_close)

	# handle obtaining general metadata here: index 0 to indices_open[0] 
	prestring = raw[:indices_open[0]-1]
	
	data['meta'] = {line.split('\t')[0]:line.split('\t')[1] for line in prestring.split('\n')}

	data['nums'] = []
	
	for i in range(len(indices_open)): # handle dynamic obtaining of meta data with a segment name here.
		a,b = indices_open[i], indices_close[i]
		try:
			a2 = indices_open[i+1]
		except IndexError:
			a2 = len(raw)

		# test if the [step] header is used.
		if raw[a:b+1] == '[step]':
			num_data_dict = {}
			# handle obtaining of numerical data headers here.
			num_string_raw = raw[b+2:a2]

			num_string_lines = [line for line in num_string_raw.split('\n')]
			num_data_dict['program'] = num_string_lines[0]
			num_data_dict['measurements'] = num_string_lines[1].split('\t')
			num_data_dict['units'] = num_string_lines[2].split('\t')

			# handle obtaining of numerical data here. after indices_close[-1].
			num_data = [line.split('\t') for line in num_string_lines[3:]]
			num_data = [[float(num.replace(',','.')) for num in tup] for tup in num_data if '' not in tup]
			num_data_dict['num_data'] = num_data

			data['nums'].append(num_data_dict)

		else:
			segment_name = raw[a+1:b]
			segment_string = raw[b+2:a2-1]

			fields = {line.split('\t')[0]:line.split('\t')[1] for line in segment_string.split('\n')}
			data[segment_name] = fields

	return data



def json_writer(data,path,indent=4):

	'''Write a dict (data) to a json file at (path).'''

	with open(path,'w',encoding='utf8') as outf:
		json.dump(data,outf,indent=indent,ensure_ascii=False)




def get_key_index(alias,measurements):

	'''Finds the index of a certian variable (like Temperature) based on an alias from the data['measurements'] section
	of the data input.'''

	for i in range(len(measurements)):
		if alias.strip().lower() in measurements[i].strip().lower():
			return i 




def plot_SDT(data,outfile):

	# dynamically detect number of data series.

	def toggle_visibility(label):

		'''Callback function for rax Checkbox.'''
	
		ind = label_index_dict[label]	
		ax.lines[ind].set_visible(not ax.lines[ind].get_visible())
		
		fig.canvas.draw()


	label_index_dict = {}

	fig = plt.figure(figsize=(10,3)) 
	gs = gridspec.GridSpec(1, 2, width_ratios=[2, 1])
	ax = plt.subplot(gs[0])
	rax = plt.subplot(gs[1]) 
	gs.update(wspace=0.05)

	for i in range(len(data['nums'])):
		num_data = data['nums'][i]
		measurements = num_data['measurements']
		label = num_data['program']

		t_ind = get_key_index('time',measurements)
		T_ind = get_key_index('temp',measurements)
		HF_ind = get_key_index('heat',measurements)

		t = np.array(num_data['num_data'])[:,t_ind]
		T = np.array(num_data['num_data'])[:,T_ind]
		HF = np.array(num_data['num_data'])[:,HF_ind]

		t_unit = num_data['units'][t_ind]
		T_unit = num_data['units'][T_ind]
		HF_unit = num_data['units'][HF_ind]
		
		ax.plot(T,HF,lw=0.7,label=label,alpha=0.5,color=cm.get_cmap('jet')(i/len(data['nums'])))
		label_index_dict[str(i+1)+'.'+label] = i


	x_label = r'$T \quad / \quad \mathrm{%s}$'%T_unit
	y_label = r'$\mathrm{Heat\;Flow} \quad / \quad \mathrm{%s}$'%HF_unit # no space for some reason

	ax.set_xlabel(x_label, size=12)
	ax.set_ylabel(y_label, size=12, labelpad=7)

	ax.xaxis.set_major_locator(MultipleLocator(50))
	ax.xaxis.set_minor_locator(AutoMinorLocator())
	
	ax.yaxis.set_major_locator(MultipleLocator(0.1))
	ax.yaxis.set_minor_locator(AutoMinorLocator())

	ax.xaxis.set_ticks_position('bottom')
	ax.tick_params(axis='both',which='both',labelsize=10, direction='in')
	
	ax.legend(loc='best',fontsize=6)

	# here checkbox logic 
	label_props = {'fontsize':[8]*4}
	frame_props={'edgecolor': None}
	check_props={'sizes':[200]*4,'color':[cm.get_cmap('jet')(i/len(data['nums'])) for i in range(len(data['nums']))]}
	
	checkbox = CheckButtons(rax, label_index_dict.keys(),
		actives=[True]*len(ax.lines),
		label_props=label_props,
		frame_props=frame_props,
		check_props=check_props)

	rax.axis('off')
	checkbox.on_clicked(toggle_visibility)

	if not args.silent:
		plt.show()
	else:
		# checkbox.remove() 
		# plt.autoscale()
		plt.savefig(outfile,dpi=500, bbox_inches='tight', transparent=False)
	


d_input = [file for file in os.listdir() if '-DSC' in file and os.path.splitext(file)[1] == '.txt'][0]
d_ext = 'png'
d_output = '.'.join((os.path.splitext(d_input)[0],d_ext))

parser = argparse.ArgumentParser(description='Creates a plot of a Trios DSC outputfile, which has been exported to plaintext (.txt)')
parser.add_argument('-i', '--input_file', default=d_input, help='Specify the input files.')
parser.add_argument('-o', '--output_file', default=d_output, help='Specify the output files.')
parser.add_argument('-x', '--extension', default=d_ext, help='Specify the output file\'s extension.')
parser.add_argument('-s', '--silent', action='store_true', help='Run in silent mode. Do not open interactive')
args = parser.parse_args()

infile = args.input_file
outfile = '.'.join((os.path.splitext(infile)[0],args.extension))

data = file_reader(infile)

plot_SDT(data,outfile)