import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import *
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

#SET UP TESTING
#set driver options
options = webdriver.ChromeOptions()
#Ignore non-critical errors
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_experimental_option("excludeSwitches", ["enable-logging"])
#set driver
driver = webdriver.Chrome(ChromeDriverManager().install(), options = options)
#driver wait
wait = WebDriverWait

#USEFUL XPATHS
USERNAME = '//*[@id="username"]'
PASSWORD = '//*[@id="password"]'
LOGIN_BUTTON = '//*[@id="submit"]'

SECURITY_BUTTON = '//*[@id="details-button"]'
CONT_LINK = '//*[@id="proceed-link"]'

TERMINAL_TAB = '//*[@id="mt1-ptmp"]'
DEVICE_TAB = '//*[@id="st15b-ptmp"]'

GPS_STATUS = '//*[@id="GPSStatus"]'

#GET REMOTE IPs
#Create dataframe from excel
sheet = pd.read_excel('PUT_ENGR_DOC_XLSX_HERE')
df = pd.DataFrame(data=sheet)
#Trim to just remotes and their IPs
df_remotes = df[['Remote Radios ','ID','IP Address']]
#Drop blank rows
df_remotes = df_remotes.dropna()
#Get number of rows as range, use this number to index through list
index = list(range(df_remotes.shape[0]))
#Initialize results db
df_results = pd.DataFrame(columns = ['Remote', 'IP Address', 'Error'], index=index)
#Initialize excel writer
writer = pd.ExcelWriter('results.xlsx')

def writeError(remote, index, ip_addr, error):
    #Update dataframe
    df_results.at[index,'Remote'] = remote
    df_results.at[index,'IP Address'] = ip_addr
    df_results.at[index,'Error'] = error


def Login(ip_addr, index):
    #3 Possible Cases - good login, security page, login not populating
    
    #Check search success
    try:
        driver.get(f'http://{ip_addr}/login.html')
    except:
        #Radio may not exist in production
        remote = df_remotes.iloc[index]['Remote Radios ']
        error = 'DNE'
        writeError(remote, index, ip_addr, error)
        return False

    try:
        #Check for regular login page
        assert 'Please sign in with your username and password.' in driver.page_source
        wait(driver,30).until(EC.presence_of_element_located((By.XPATH, LOGIN_BUTTON)))
        assert driver.find_element(By.XPATH, LOGIN_BUTTON).is_enabled()
    except:
            try:
                #Check for security warning and navigate it, then check for regular login again
                assert "Your connection is not private" in driver.page_source
                wait(driver,30).until(EC.presence_of_element_located((By.XPATH, SECURITY_BUTTON)))
                driver.find_element(By.XPATH, SECURITY_BUTTON).click()
                wait(driver,30).until(EC.presence_of_element_located((By.XPATH, CONT_LINK)))
                driver.find_element(By.XPATH, CONT_LINK).click()
                assert 'Please sign in with your username and password.' in driver.page_source
                wait(driver,30).until(EC.presence_of_element_located((By.XPATH, LOGIN_BUTTON)))
                assert driver.find_element(By.XPATH, LOGIN_BUTTON).is_enabled()
            except:
                try:
                    #Check that login button is enabled, try refreshing until it is (max 5 attempts)
                    for attempt in range(0,4):
                        if not driver.find_element(By.XPATH, LOGIN_BUTTON).is_enabled():
                            driver.refresh()
                            wait(driver,30).until(EC.presence_of_element_located((By.XPATH, LOGIN_BUTTON)))
                        else:
                            break
                    assert driver.find_element(By.XPATH, LOGIN_BUTTON).is_enabled()
                except:
                    #Radio is not populating login button (slow connection)
                    remote = df_remotes.iloc[index]['Remote Radios ']
                    error = 'SLOW'
                    writeError(remote, index, ip_addr, error)
                    return False
    
    #Log in
    wait(driver,45).until(EC.presence_of_element_located((By.XPATH, LOGIN_BUTTON)))
    user = driver.find_element(By.XPATH, USERNAME)
    pw = driver.find_element(By.XPATH, PASSWORD)
    
    #2 Cases - managed password and default password
    try:
        user.send_keys("PUT_USER_HERE")
        pw.send_keys("PUT_PWD_HERE")
        pw.send_keys(Keys.RETURN)
        wait(driver,15).until(EC.url_changes)         
    except:
        user.send_keys("PUT_USER_HERE")
        pw.send_keys("PUT_PWD_HERE")
        pw.send_keys(Keys.RETURN)
        wait(driver,15).until(EC.url_changes)
    return True
   
def Test(ip_addr, index):
    #Navigate through radio web ui
    try:
        #Click device tab
        wait(driver,30).until(EC.presence_of_element_located((By.XPATH, DEVICE_TAB)))
        driver.find_element(By.XPATH, DEVICE_TAB).click()
    except:
        try:
            #Try refreshing
            driver.refresh()
            wait(driver,30).until(EC.presence_of_element_located((By.XPATH, DEVICE_TAB)))
            driver.find_element(By.XPATH, DEVICE_TAB).click()
        except:
            #Radio is not populating settings (slow connection)
            remote = df_remotes.iloc[index]['Remote Radios ']
            error = 'SLOW'
            writeError(remote, index, ip_addr, error)
            return False
    try:
        #Find GPS web element and get text
        wait(driver,30).until(EC.presence_of_element_located((By.XPATH, GPS_STATUS)))
        GPS = driver.find_element(By.XPATH, GPS_STATUS).text
    except:
        try:
            #Try refreshing
            driver.refresh()
            wait(driver,30).until(EC.presence_of_element_located((By.XPATH, GPS_STATUS)))
            GPS = driver.find_element(By.XPATH, GPS_STATUS).text
            #This is the bug - GPS element does not populate
            if GPS == "":
                return True
            else:
                return False
        except:
            #Radio is not populating settings (slow connection)
            remote = df_remotes.iloc[index]['Remote Radios ']
            error = 'SLOW'
            writeError(remote, index, ip_addr, error)
            return False
    
def main(index):
    #Get IP at index
    ip_addr = df_remotes.iloc[index]['IP Address']
    #Clear any spaces - correcting error in documentation
    ip_addr = ip_addr.replace(" ", "")
    print('Looking at... | Index '+str(index) +' | IP: '+str(ip_addr))
    #Main process
    if Login(ip_addr, index):
        if Test(ip_addr,index):
            remote = df_remotes.iloc[index]['Remote Radios ']
            error = 'BUG!'
            writeError(remote, index, ip_addr, error)
    #Write results to excel file
    df_results.to_excel(writer)
    #Save excel file
    writer.save()

##START CODE
if __name__ == '__main__':
    main()