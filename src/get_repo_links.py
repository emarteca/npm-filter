
# set of functions for extracting lists of repos to clone 
# from a variety of sources

# from a file that's just a list of github repos 
# of the form: https://github.com/username/reponame
# optionally, users can specify a particular commit SHA to run over
# this should be separated from the repo by some whitespace
def from_list_of_repos( filename):
	with open(filename) as f:
		file_lines = f.read().split("\n")
	# filter out empty lines and return
	return( [ f for f in file_lines if len(f) > 0]) 