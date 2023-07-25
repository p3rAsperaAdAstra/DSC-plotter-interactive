import os 
import re 
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
# do not use \n[[a-zA-Z]\s]+\n type strings in the comment section of the file. The script will not be able to find all the data inside the "csv" file
# add option to plot from cmd only providing dir.
# add color selection options
# create default dict like in other scripts.


# Helper functions for argparse defaults
def get_default_input(directory=''):

	'''Dynamically determine input file if none found.'''

	if directory != '': directory = os.path.join(directory,'*.txt')

	files = glob('%s*.txt'%directory)

	for file in files:
		with open(file) as inf:
			if '\n[step]\n' in inf.read():
				return file


defaults = {'input_file':get_default_input(),
			'extension':'png',
			'silent':False,
			'colors':None} # add options

defaults['output_file'] = os.path.splitext(defaults['input_file'])[0] + '.' + defaults['extension']

parser = argparse.ArgumentParser(description='Creates a plot of a Trios DSC outputfile, which has been exported to plaintext (.txt)')
parser.add_argument('-i', '--input_file', default=defaults['input_file'], help='Specify the input files.')
parser.add_argument('-o', '--output_file', default=defaults['output_file'], help='Specify the output files.')
parser.add_argument('-x', '--extension', default=defaults['extension'], help='Specify the output file\'s extension.')
parser.add_argument('-s', '--silent', default=defaults['silent'], action='store_true', help='Run in silent mode. Do not open interactive')
parser.add_argument('-c', '--colors', default=defaults['extension'], help='Specify the output file\'s extension.')
args = parser.parse_args()



def get_data(path:str):

	'''Reads in a TRIOS output file (export to .csv in trios software) for a DSC measurement. 
	Input: Path (str)
	Output: Data (dict).'''

	def find_section_indices(string:str):

		'''Searches the entire file string for the the section titles and returns their indices as
		a list of tuples.'''

		section_rex = r'\n\[[\w\s]+\]\n'
		start_indices = []
		end_indices = []
		section_titles = []
		num_steps = 0

		for match in re.finditer(section_rex,string):
			start_indices.append(match.start())
			end_indices.append(match.end())
			section_titles.append(match.group()[2:-2])

			if match.group() == '\n[step]\n': num_steps += 1 # find out how many steps are in the file 

		len_mismatch_msg = '''The amount of opening and closing angular brackets is not identical.
		This means that the regex is not finding all the sections of the trios file.
		Contact someone to fix this, or find out why section_rex is not capturing correctly.'''

		assert len(start_indices) == len(end_indices) == len(section_titles), len_mismatch_msg

		return start_indices,end_indices,section_titles,num_steps



	with open(path,'r',encoding='utf8') as inf:
		raw = inf.read() # read in entire file as one string.

	raw = '\n[general]\n' + raw

	start_indices, end_indices, section_titles, num_steps = find_section_indices(raw) # find the indices of the different sections inside the file.
	data = {} # this is where the data will end up.
	data['meta'] = {}
	data['steps'] = []
	
	# meta_string = raw[:start_indices[-num_steps]] # put meta data part of the string in a separate variable
	# num_string = raw[start_indices[-num_steps]:]
	# print(num_string)
	
	# obtain the different meta data sections as dict.
	for i in range(len(start_indices)-num_steps):
		section_title = section_titles[i]
		sec_start = start_indices[i] + len(section_title)
		sec_end = start_indices[i+1]
		section = raw[sec_start+4:sec_end]
		
		data['meta'][section_title] = {line.split('\t')[0]:line.split('\t')[1] for line in section.split('\n')}
	
	# obtain the different heat ramp numerical info
	start_indices += [len(raw)] # add len of file so that slicing has a concrete end point.
	for i in range(len(section_titles)):
		if section_titles[i].strip().lower() == 'step':
			step_data = {}
			
			sec_start = end_indices[i]
			sec_end = start_indices[i+1]
			section = raw[sec_start:sec_end-1]
			lines = section.split('\n')
			
			# probs not very reliable for different kinds of out files.
			step_data['program'] = lines[0]
			step_data['variables'] = lines[1].split('\t')
			step_data['units'] = lines[2].split('\t')

			# get the numerical data. might have to do regex search in later release. 
			step_data['num'] = [[float(num) for num in line.replace(',','.').split('\t') if num != ''] for line in lines[3:] if line != '']
			
			data['steps'].append(step_data)

	return data
	



def json_writer(data:dict,path:str,indent=4):

	'''Write the data (dict) to a json file. Location is specified by path (str).'''

	with open(path,'w',encoding='utf8') as outf:
		json.dump(data,outf,indent=indent,ensure_ascii=False)




def get_key_index(alias:str,steps:list):

	'''Finds the index of a certian variable (like Temperature) based on an alias from the data['measurements'] section
	of the data input.'''

	for i in range(len(steps)):
		if alias.strip().lower() in steps[i].strip().lower():
			return i 




def plot_SDT(data:dict,outfile:str):

	'''The actual plotting function. Takes the data (dict) from '''

	def toggle_visibility(label:str):

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

	for i in range(len(data['steps'])):
		num_data = data['steps'][i]['num'] 
		variables = data['steps'][i]['variables']
		label = data['steps'][i]['program']

		num_data = [tup for tup in num_data if len(tup) == len(variables)] # remove incomplete entries in num data

		t_ind = get_key_index('time',variables)
		T_ind = get_key_index('temp',variables)
		HF_ind = get_key_index('heat',variables)

		t = np.array(num_data)[:,t_ind]
		T = np.array(num_data)[:,T_ind]
		HF = np.array(num_data)[:,HF_ind]

		t_unit = variables[t_ind]
		T_unit = variables[T_ind]
		HF_unit = variables[HF_ind]
		
		ax.plot(T,HF,lw=0.7,label=label,alpha=0.5) # add color controls
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
	frame_props = {'edgecolor': [ax.lines[i].get_color() for i in range(len(ax.lines))]}
	check_props = {'sizes':[200]*4,'color':[ax.lines[i].get_color() for i in range(len(ax.lines))]}
	
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
	


infile = args.input_file

if os.path.isdir(infile):
	infile = get_default_input()

data = get_data(infile)
plot_SDT(data,args.output_file)