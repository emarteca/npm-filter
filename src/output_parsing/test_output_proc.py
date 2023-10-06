import json
import xmltodict
import pandas as pd
 
# parse the output of mocha xunit reporter to a csv
# does not delete the original xunit output file
# outputs include, per test (in this order):
# - test suite it's a part of
# - name of the test itself
# - runtime of the test
# - stdout of the test (if any)
# - pass/fail status (could also be "pending")
def parse_mocha_json_to_csv(output_file, new_output_file=None):
    if new_output_file is None:
        new_output_file = output_file.split(".")[0] + ".csv" # same name, csv file extension
    # convert an xml file to json
    # used to convert the xunit reporter output from mocha into json 
    # code from https://www.geeksforgeeks.org/python-xml-to-json/
    data_dict = {}
    try:
        with open(output_file) as xml_file:
            data_dict = xmltodict.parse(xml_file.read()).get("testsuite", {})
    except:
        data_dict = {}
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
            test_pass_fail += ["failed"]
        else:
            test_stdout += [""]
            test_pass_fail += ["passed"]
    res_df = pd.DataFrame(list(zip(test_suites, test_names, test_runtimes, test_stdout, test_pass_fail)))
    try:
        res_df.columns = ["test_suite", "name", "runtime", "stdout", "pass_fail"]
        with open(new_output_file, 'w') as csv_file:
            csv_file.write(res_df.to_csv())
    except:
        print("ERROR in data for file " + new_output_file + " -- no output printed. skipping to next step...")

# parse the output of jest xunit reporter to a csv
# this does the same thing as for mocha, to produce the same data fields
# does not delete the original xunit output file
# outputs include, per test (in this order):
# - test suite it's a part of
# - name of the test itself
# - runtime of the test
# - stdout of the test (if any)
# - pass/fail status (could also be "pending")
def parse_jest_json_to_csv(output_file, new_output_file=None):
    if new_output_file is None:
        new_output_file = output_file.split(".")[0] + ".csv" # same name, csv file extension
    data_dict = {}
    try:
        with open(output_file) as json_file:
            data_dict = json.loads(json_file.read())
    except:
        data_dict = {}
    # the format: all tests are in a top level list called "testResults"
    # this is a list of objects that have "assertionResults" representing the test suites
    # "assertionResults" is a list of objects that have the test data
    test_suites = []
    test_names = []
    test_runtimes = []
    test_stdout = []
    test_pass_fail = []
    for test_suite in data_dict.get("testResults", []):
        test_suite_results = test_suite.get("assertionResults", [])
        test_suite_name = test_suite.get("name", "")
        for test_results in test_suite_results:
            test_status = test_results.get("status", "failed")
            test_duration = test_results.get("duration")
            # if it can't convert to a string, could be missing/nonetype (None duration for pending tests)
            try:
                test_duration = float(test_duration)
            except:
                test_duration = float("NaN")
            test_suites += [test_suite_name]
            test_names += [test_results.get("fullName", "")]
            test_runtimes += [test_duration]
            test_stdout += [";".join(test_results.get("failureMessages", []))]
            test_pass_fail += [test_status] # passed/failed/pending -- if not present assume failed
    res_df = pd.DataFrame(list(zip(test_suites, test_names, test_runtimes, test_stdout, test_pass_fail)))
    try:
        res_df.columns = ["test_suite", "name", "runtime", "stdout", "pass_fail"]
        with open(new_output_file, 'w') as csv_file:
            csv_file.write(res_df.to_csv())
    except:
        print("ERROR in data for file " + new_output_file + " -- no output printed. skipping to next step...")