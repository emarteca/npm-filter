import json
import xmltodict
import pandas as pd
 
def parse_mocha_json_to_csv(output_file, new_output_file=None):
    if new_output_file is None:
        new_output_file = output_file.split(".")[0] + ".csv" # same name, csv file extension
    # convert an xml file to json
    # used to convert the xunit reporter output from mocha into json 
    # code from https://www.geeksforgeeks.org/python-xml-to-json/
    with open(output_file) as xml_file:
        data_dict = xmltodict.parse(xml_file.read()).get("testsuite", {})
    # the format: all the tests are in a top-level list called "testcase"
    test_suites = []
    test_names = []
    test_runtimes = []
    test_stdout = []
    test_pass_fail = []
    for test in data_dict.get("testcase", []):
        test_suites += [test.get("@classname", "").strip()]
        test_names += [test.get("@name", "").strip()]
        test_runtimes += [float(test.get("@time", "NaN"))]
        if test.get("failure", False):
            test_stdout += [test["failure"]]
            test_pass_fail += ["Fail"]
        else:
            test_stdout += [""]
            test_pass_fail += ["Pass"]
    res_df = pd.DataFrame(list(zip(test_suites, test_names, test_runtimes, test_stdout, test_pass_fail)))
    res_df.columns = ["test_suite", "name", "runtime", "stdout", "pass_fail"]
    with open(new_output_file, 'w') as csv_file:
        csv_file.write(res_df.to_csv())