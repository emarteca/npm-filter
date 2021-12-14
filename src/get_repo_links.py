
# set of functions for extracting lists of repos to clone 
# from a variety of sources


# output from old QL queries (pre-json), with counts from grep
# lines in this file look like:
# DFEAGILEDEVOPS/MTC/output.csv:5
# and we want to extract:
# https://github.com/DFEAGILEDEVOPS/MTC.git if cutoff < 5
def from_grepped_old_QL_output( filename, cutoff=0):
	with open(filename) as f:
		file_lines = f.read().split("\n")
	start_link = "https://github.com/"
	end_link = ""
	return([ start_link + line.split(":")[0].split("/output.csv")[0] + end_link 
						for line in file_lines if int(line.split(":")[1]) >= cutoff ])

# from a file that's just a list of github repos 
# of the form: https://github.com/username/reponame
# optionally, users can specify a particular commit SHA to run over
# this should be separated from the repo by some whitespace
def from_list_of_repos( filename):
	with open(filename) as f:
		file_lines = f.read().split("\n")
	# filter out empty lines and return
	return( [ f for f in file_lines if len(f) > 0]) 