#Potential Humanity-Timekeeping Headache Reducer
import re
import calendar
from datetime import timedelta
from datetime import datetime as dt
import math
from bs4 import BeautifulSoup
import requests
import mechanize
import http.cookiejar as cookielib
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

#perhaps turn into a dictionary with Month/days as keys, and values being a dictionary of type_of_shift:duration of shift

#parse it a lot

#credit for the structure of the function goes to 
#https://www.codegrepper.com/code-examples/python/converting+to+military+time+in+python, 
#written by Better Boar
#only works on these use-cases really. 
#non-military times formatted like 1:54am or 4:36aM or 11:43PM work, can't do 01:54am
def convertToMilitaryTime(s): 
   s = s.upper()
   if s[-2:] == "AM":
      if s[:2] == '12': #12AM case
          hour = 0
          minute = s[3:5]
      else:
          if len(s) == 6:  #if hour has 1 digit
              hour = s[0]
              minute = s[2:4]
          else:            #if hour has 2 digits
              hour = s[:2]
              minute = s[3:5]
   else:
      if s[:2] == '12': #12PM case
          hour = 12
          minute = s[3:5]
      else:
      	  if len(s) == 6:  #if hour has 1 digit
      	  	  hour = 12 + int(s[0])
      	  	  minute = s[2:4]
      	  else:            #if hour has 2 digits
              hour = 12 + int(s[0:2])
              minute = s[3:5]
   return timedelta(hours=int(hour), minutes=int(minute))

def is_partially_midnight_rounds_shift(start_time, end_time): #start_end_str in format: 1:56pm 3:22pm
    return ((end_time > timedelta(hours=21,minutes=15)) or (end_time < timedelta(hours=3,minutes=30)))# maybe add this condition if I support rounds shifts exclusively as well: and start_time < timedelta(hours=21,minutes=40)

def subtract_midnight_rounds_time_from_total_duration(start_time, end_time): #takes start and end timestraight from data "1:56pm 12:03pm"
    original_dur = end_time - start_time
    rounds_dur = end_time - timedelta(hours=21,minutes=0)
    result_dur = str(original_dur - rounds_dur)
                                 #adjusted end_time to disclude time 
                                 #after 10PM/during rounds shift.
    return result_dur #return actual desk shift duration in string form for easy concatenation/modification

def round_to_hundredths(n): #code from https://realpython.com/python-rounding/ 
    multiplier = 10 ** 2
    return math.floor(n*multiplier + 0.5) / multiplier

def clean_data(data): #puts data in (hours) hours (minutes)m (month) (day) format
    partial_rounds_shifts = []
    for i in range(0, len(data)):
        match_mins = re.search("[0-9][0-9]?m", data[i])
        match_month_day = re.search("[A-Z][a-z]{2} [0-9][0-9]?", data[i])
        match_start_and_end_times = re.search("[0-9][0-9]?:[0-9]{2}[a,p]m [0-9][0-9]?:[0-9]{2}[a,p]m", data[i])
        if data[i][1] == "h": #duration hours are 1 digit
            hours = data[i][0]
        else: #duration hours are 2 digits
            hours = data[i][0:2]
        if match_mins == None:
            print("Invalid. No minute data was included!")
        elif match_month_day == None:
            print("Invalid. No hour data was included!")
        elif match_start_and_end_times == None:
            print("Invalid. No start or end time data was included!")
        else:           
            minutes = match_mins.group().replace("m", "")
            month_day = match_month_day.group()
            start_and_end_times = match_start_and_end_times.group()
            start_time = convertToMilitaryTime(start_and_end_times[0:6]) 
            end_time = convertToMilitaryTime(start_and_end_times[7:-1] + start_and_end_times[-1])
            shift_type = "Cons Shift"
            if start_time < timedelta(hours=12, minutes=0):
                shift_type = ask_morning_shift_type(month_day)
            if is_partially_midnight_rounds_shift(start_time, end_time):
                adjusted_dur = subtract_midnight_rounds_time_from_total_duration(start_time, end_time)
                night_rounds_dur = str(end_time - timedelta(hours=21,minutes=0))
                if adjusted_dur[1] == ":": #adjusted duration hours are 1 digit
                    night_rounds_hours = night_rounds_dur[0]
                    night_rounds_minutes = night_rounds_dur[2:4]
                    hours = adjusted_dur[0]
                    minutes = adjusted_dur[2:4] #+ "m" #put in (minutes)m format
                    #minutes = minutes[0].replace("0", "") + minutes[1:] #get rid of any leading zero
                else: #adjusted duration hours are 2 digits
                    night_rounds_hours = night_rounds_dur[0:2]
                    night_rounds_minutes = night_rounds_dur[3:5] #+ "m" #put in (minutes)m format
                    night_rounds_minutes = rounds_minutes[0].replace("0", "")
                    hours = adjusted_dur[0:2]
                    minutes = adjusted_dur[3:5] #+ "m" #put in (minutes)m format
                    minutes = minutes[0].replace("0", "") #+ minutes[1:] #get rid of any leading zero
                partial_rounds_shifts.append(f"{round_to_hundredths(float(night_rounds_hours) + float(night_rounds_minutes)/60)} hours {month_day} Rounds Shift")
           # if len(minutes) == 1: #case if 0 minutes
           #     minutes = "0m"
            data[i] = f"{round_to_hundredths(float(hours) + float(minutes)/60)} hours {month_day} {shift_type}"
    data = data[::-1] + partial_rounds_shifts
    return data
     #   make_timedelta_list(match_start_and_end_times.group())

def login(driver):

    username = input("Please enter your username for Humanity. ")
    password = input("Please enter your password for Humanity. ")
    driver.get("https://nu1.humanity.com/app/timeclock/")
    driver.find_element("id", "email").send_keys(username)
    # find password input field and insert password as well
    driver.find_element("id", "password").send_keys(password)
    # click login button when clickable
    WebDriverWait(driver,10).until(EC.element_to_be_clickable( (By.NAME, "login") )).click()
def record_timeclock_data(driver):
    WebDriverWait(driver,10).until(EC.element_to_be_clickable( (By.ID, "sn_timeclock") )).click()
    timesheet_select_xpath = "//body[contains(@id, '_fbody')]//table//tbody//td//div[contains(@id, '_cd_timeclock')]//div[contains(@class, 'right')]//table//tbody//tr//td[2]//div//div//div"
    #driver.find_element("xpath", timesheet_select_xpath).click()
    WebDriverWait(driver,10).until(EC.element_to_be_clickable( (By.XPATH, timesheet_select_xpath) )).click()
    WebDriverWait(driver,10).until(EC.element_to_be_clickable( (By.XPATH, timesheet_select_xpath + "//ul//a[contains(@rel, 'This Week')]") )).click()
    
    #driver.find_element("xpath", timesheet_select_xpath + "//ul//a[contains(@rel, 'This Week')]").click()
    time.sleep(1)
    times_list = WebDriverWait(driver,10).until(EC.presence_of_element_located( (By.XPATH, "//body[contains(@id, '_fbody')]//table//tbody//td//div[contains(@id, '_cd_timeclock')]//div[contains(@class, 'right')]//table//tbody//tr//td[2]//div//ul[contains(@class, 'timeSList')]") ))
    #times_list = driver.find_element("xpath", "//body[contains(@id, '_fbody')]//table//tbody//td//div[contains(@id, '_cd_timeclock')]//div[contains(@class, 'right')]//table//tbody//tr//td[2]//div//ul[contains(@class, 'timeSList')]")
    return times_list

def write_timeclock_data_to_txt(data):
    with open("clockindata.txt", 'w', encoding = 'utf-8') as f:
        f.seek(0)
        f.truncate()
        f.write(str(data.text))

def read_data_from_txt(driver):
    with open("clockindata.txt", 'r', encoding = 'utf-8') as f:
        lst_of_lines = f.readlines()
        for i in range(0, len(lst_of_lines) - 5):
            lst_of_lines[i : i+5] = [''.join(lst_of_lines[i : i+5]).replace("\n", "").lstrip()]
            #above line: merge every 5 elements in clockindata.txt and massage the string to a better format
    lst_of_lines = [x for x in lst_of_lines if x != ""] #filter out "" garbage 
    lst_of_lines.pop(0) #get rid of the ul header

    for i in range(len(lst_of_lines)): #case of 0hrs
    	if lst_of_lines[i][1] == "m":
    		lst_of_lines[i] = "0h, " + lst_of_lines[i]
    print(lst_of_lines) #for debugging calculations
    return lst_of_lines

def calculate_my_hours():
    driver = webdriver.Chrome("chromedriver", 110)
    login(driver)
    data = record_timeclock_data(driver)
    write_timeclock_data_to_txt(data)
    my_data = read_data_from_txt(driver)
    driver.close() 
    my_data = clean_data(my_data)
    return my_data

def ask_morning_shift_type(date):
    while True:
        is_morning_rounds = input(f"Was your morning shift on {date} a Rounds shift? Y/N ")
        is_morning_rounds = is_morning_rounds.upper().strip()
        if is_morning_rounds == "Y":
        	return "Rounds Shift"
        elif is_morning_rounds == "N":
        	return "Cons Shift"
        else:
        	print("\nPlease respond with either Y or N, please.\n") 

print(calculate_my_hours())
date = '09 23 2001'
born = dt.strptime(date, "%m %d %Y").weekday()
#sprint(calendar.day_name[born])
#2. DATETIME
#3. Handle partial morning rounds into cons
#2=4. Handle 5-7PM friday rounds
#5. Add friday training hours, prolly ask_training "did you have training on BOTH fridays, only the FIRST friday, or only the SECOND friday"
#6. little prompt that tells the user to enter any special hours
#Catch ERR_INTERNET_DISCONNECTED
#Allow for inputted username/password
#Make user-friendly (good comments, more readable code, ui, webdriverwait, get rid of on-screen webdriver, update chromedriver automatically)
#Maybe make automation-less version
#Submit to timekeeping 
