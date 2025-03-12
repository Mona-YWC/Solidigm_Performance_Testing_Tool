# Solidigm_Performance_Testing_Tool



Step1: 
./setup.sh 
Optional: pip install -r requirements.txt

Note: The test results on the GIGABYTE Rack Server - R283-Z96-AAE1 - AMD EPYC™ 9004 have PASSed.

Before testing Solidigm_8corner_fio_test.py, you need to run "setup.sh" first. This bash script serves the following purposes:
(1) Verify that the Python version on the test platform meets the requirements.
(2) Automatically execute requirements.txt to ensure all necessary packages are installed.
Please run setup.sh first to ensure the environment is properly set up before proceeding with the test.
If the Python version in your test environment is already 3.x, you can simply run pip install -r requirements.txt to install the dependencies.

Step2: 
./SUT_Provisioning.py

Note: The test results on the GIGABYTE Rack Server - R283-Z96-AAE1 - AMD EPYC™ 9004 have PASSed.

SUT_Provisioning.py will create a file named "Solidigm_Testing_Result_+ execution timestamp", then configure OS-related settings, such as disabling CPU power-saving features. It will also save the OS and SSD information into SSD_testing_list.xlsx, helping users quickly understand the DUT (Device Under Test) details. SUT_Provisioning.py will generate script.log during execution to help users quickly debug.

Step3: 
