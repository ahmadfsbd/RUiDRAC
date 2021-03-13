import time
import pdb
import json
import sys
import os
from concurrent import futures
import pip

try:
    import selenium
except:
    pip.main(['install', 'selenium'])
    time.sleep(2)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

file_path = ""
chrome_driver = ""
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--incognito")
drivers = []
updated_servers = []
failed_servers = []
num = 3  # number of simultaneous threads to update servers


# A function to logout from iDRAC9
def logout_from_idrac(driver):
    try:
        print("Logging out from iDRAC")
        elem = driver.find_element_by_xpath("//i[@class='ci ci-color-white ci-user-profile-core dropdown-toggle']").click()
        elem = elem = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH,"//a[contains(text(),'Logout')]")))
        elem.click()
        time.sleep(1)
    except:
        pass


# Divide servers into "num"(ie 2,3,4) sub lists
def chunkIt(servers, num):
    avg = len(servers) / float(num)
    out = []
    last = 0.0

    while last < len(servers):
        out.append(servers[int(last):int(last + avg)])
        last += avg
    return out


# Function to update firmware of a single server
def update(file_path, server):
    global updated_servers, failed_servers, chrome_driver, chrome_options, drivers
    try:
        # Get server credentials
        url = server["url"]
        username = server["username"]
        password = server["password"]
        path = file_path
        flag = False  # flag to check if webdriver is running
        in_progress = False

        # open webdriver
        try:
            print("Opening WebDriver for %s" % url)
            driver = webdriver.Chrome(chrome_driver)
            # headless chrome (To  use this uncomment the line below and comment out the statement above
            ###################################################################
            #driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)
            ###################################################################
            # Access iDRAC
            flag = True
            drivers.append(driver)
            driver.implicitly_wait(10)
            driver.get(url)
        except:
            print("Failed to open WebDriver for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                driver.close()
            failed_servers.append(url)
            return

        # login
        try:
            # login using credentials for iDRAC
            print("Logging in for server: %s" % url)
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, """username""")))
            element = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.NAME, """username""")))
            element.send_keys(username)
            driver.find_element_by_name('password').send_keys(password)
            driver.find_element_by_xpath('''//button[@type='submit']''').click()
            time.sleep(4)
        except:
            print("Failed to login for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))

            if flag:
                driver.close()
            failed_servers.append(url)
            return

        # Go to Maintainence Section
        try:
            try:
                # Find And Click Drop Down List
                print("Finding and clicking dropdown list for server: %s" % url)
                # assert "Dashboard" in driver.title
                element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//div[@class='menu-div ng-scope']//span[2]""")))
                element = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, """//div[@class='menu-div ng-scope']//span[2]""")))
                element.click()
            except:
                print("DropDown List not found for server: %s. Moving on!" % url)
                print("Error: " + str(sys.exc_info()[0]))
                print("Cause: " + str(sys.exc_info()[1]))
                print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
                pass
            # Click Maintainence Tab
            print("Clicking the mainainence tab for server: %s" % url)
            element = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, """//strong[@id='maintenance']""")))
            element.click()
            time.sleep(4)
        except:
            print("Failed to reach maintainence section for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                logout_from_idrac(driver)
                driver.close()
            failed_servers.append(url)
            return

        # Go To Update Section
        try:
            print("Finding and clicking the update section for server: %s" % url)
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//li[@id='maintenance.systemupdate']""")))
            element = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, """//li[@id='maintenance.systemupdate']""")))
            element.click()
            # if an update is already in progress
            try:
                element = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, """//*[@id="module-div"]/div[2]/div/div[2]/div/div[2]/idrac-alert/div/span/span[2]""")))
                msg = str(element.get_attribute("outerHTML").split(">")[1].replace("</span",""))
                if "already in progress" in msg:
                    print("An update is already in progress for server: %s. Exiting!" % url)
                    if flag:
                        driver.close()
                    failed_servers.append(url)
                    return
                else:
                    pass
            except:
                pass
        except:
            print("Failed to obtain update setion for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                logout_from_idrac(driver)
                driver.close()
            failed_servers.append(url)

        time.sleep(2)

        # Add File Path
        try:
            print("Adding file path for server: %s" % url)
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//input[@name='fwfile']""")))
            element = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, """//input[@name='fwfile']""")))
            element.send_keys(path)
            print("File Path ADDED!")
            time.sleep(2)
        except:
            print("Failed to add file path for server: %s Aborting Update!")
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                logout_from_idrac(driver)
                driver.close()
            failed_servers.append(url)
            return

        # Upload File
        try:
            print("Uploading file for server: %s" % url)
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, """//button[@type='submit']""")))
            element.click()
            # Wait For Upload To Finish For 20 sec and click check box
            time.sleep(20)
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//th[@class='ng-scope']//input[@type='checkbox']""")))
            #element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, """//th[@class='ng-scope']//input[@type='checkbox']""")))
            element.click()
        except:
            print("Failed to upload the file for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                logout_from_idrac(driver)
                driver.close()
            failed_servers.append(url)
            return
        # Select Update and Restart Option
        try:
            print("Clicking Update and Restart option!")
            # To select Update and Restart Option, Comment out the following lines
            ###################################################################
            #element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//button[contains(text(),'Install and Reboot')]""")))
            #element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, """//button[contains(text(),'Install and Reboot')]""")))
            #element.click()
            ###################################################################
            # To test, comment out the following lines
            ###################################################################
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, """//*[@id="module-div"]/div[2]/div/div[2]/div/div[4]/div/button[1]""")))
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, """//*[@id="module-div"]/div[2]/div/div[2]/div/div[4]/div/button[1]""")))
            element.click()
            ###################################################################
        except:
            print("Failed to initialize update and restart option for server: %s Aborting Update!" % url)
            print("Error: " + str(sys.exc_info()[0]))
            print("Cause: " + str(sys.exc_info()[1]))
            print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
            if flag:
                logout_from_idrac(driver)
                driver.close()
            failed_servers.append(url)
            return

        # Close WebDriver and finish
        print("Update successfully started for server: %s" % url)
        time.sleep(4)
        logout_from_idrac(driver)
        driver.close()
        updated_servers.append(url)
        return

    except:
        print("Update Failed For Server : %s Aborting!" % url)
        print("Error: " + str(sys.exc_info()[0]))
        print("Cause: " + str(sys.exc_info()[1]))
        print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
        if flag:
            logout_from_idrac(driver)
            driver.close()
        failed_servers.append(url)
        return


# Thread to update a sub_list of servers
def update_servers(servers, i):
    global file_path
    if servers:
        time.sleep(0.1*i)
        print("Update thread started: Thread : %d" % i)

        for server in servers:
            update(file_path, server)
    else:
        print("No servers in sub_list, Exiting Thread: %d" % i)
    return ("Completed Thread", i)  # tell the wait functionality that thread has completed


# Divide workload
def start_threadpool(servers):
    global num  # number of simultaneous threads for updating servers
    servers = chunkIt(servers, num)  # will divide server list into "num"-number of sub_lists
    # create ThreadPool
    executor = futures.ThreadPoolExecutor(max_workers=num)
    # start a thread (update_servers) for each sublist in servers[]
    wait_for = [
        executor.submit(update_servers, servers[i], i)
        for i in range(0, num, 1)
        ]
    #  wait for threads to complete & print as each thread is done
    for f in futures.as_completed(wait_for):
        print('Thread: result: {}'.format(f.result()))


def main():
    global updated_servers, failed_servers, chrome_driver, file_path, drivers
    # Load file and server Configs
    try:
        current_dir = os.getcwd()
        chrome_driver = current_dir + "\\" + "chromedriver.exe"
        config_path = current_dir + "\\config.txt"
        configs = json.load(open(config_path))
        file_path = current_dir + "\\firmware\\" + configs["file_name"]
        servers = configs["servers"]  # a list of server dictionaries
    except:
        print("Failed to load config file! Exiting...")
        print("Error: " + str(sys.exc_info()[0]))
        print("Cause: " + str(sys.exc_info()[1]))
        print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
        time.sleep(2)
        sys.exit()

    print("Firmware Update Has Been Started!")
    start_threadpool(servers)
    print("\n:::::::::::::::::::::::::::::::::::::::::::::::")
    print(":::::::::::::::::: SUMMARY ::::::::::::::::::::")
    print("::::::::::::::::::::::::::::::::::::::::::::::: \n")
    print("Update was successfully run on the following servers:\n")
    for url in updated_servers:
        print(url)
    print("Update failed on the following servers: \n")
    for url in failed_servers:
        print(url)
    for driver in drivers:
        try:
            driver.close()
        except:
            pass
    print("\nFirmware update has finished running!")


# Run The Script if Directly Called
if __name__ == '__main__':
    try:
        # pdb.set_trace()

        main()
    except:
        print("The Main Script Has Failed! Exiting The Program.....")
        print("Error: " + str(sys.exc_info()[0]))
        print("Cause: " + str(sys.exc_info()[1]))
        print("Line No: %s \n" % (sys.exc_info()[2].tb_lineno))
        time.sleep(2)
        sys.exit(0)
