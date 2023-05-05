import json
import xmltodict
 
# convert an xml file to json
# used to convert the xunit reporter output from mocha into json
# note: this overwrites the existing file
# code from https://www.geeksforgeeks.org/python-xml-to-json/
def xml_to_json(output_file, new_output_file=None):
    if new_output_file is None:
        new_output_file = output_file
    with open(output_file) as xml_file:
        data_dict = xmltodict.parse(xml_file.read())
        json_data = json.dumps(data_dict)
        with open(new_output_file, 'w') as json_file:
            json_file.write(json_data)