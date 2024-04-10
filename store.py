from datetime import datetime,timedelta
from typing import Dict, List, Tuple
import pytz

class Store:
    '''
    class for the store with all the required data structures corresponding the store and 
    its get methods for last uptime/downtime.
    '''
    def __init__(self,store_id,time_zone):
        self.store_id: int = store_id
        self.time_zone:str = time_zone
        self.business_hours: Dict[int, Tuple[datetime,datetime]] = {}
        self.store_status: List[Tuple[datetime, int]] = []  
    def set_business_hours(self,schedule):
        utc_tz = pytz.UTC
        time_zone = pytz.timezone(self.time_zone)

        '''
        this part sets the business hours of a particular shop as 24*7 because we did not
        find any entry in the business_times table for that particular shop id and it was told
        to assume it to be open 24*7
        '''
        if len(schedule)==0:
            start_time_str = "00:00:00" 
            end_time_str = "23:59:59"

            start_time_utc = datetime.strptime(start_time_str, "%H:%M:%S")
            end_time_utc = datetime.strptime(end_time_str, "%H:%M:%S")
            self.business_hours={
                6:(start_time_utc.time(),end_time_utc.time()),
                5:(start_time_utc.time(),end_time_utc.time()),
                4:(start_time_utc.time(),end_time_utc.time()),
                3:(start_time_utc.time(),end_time_utc.time()),
                2:(start_time_utc.time(),end_time_utc.time()),
                1:(start_time_utc.time(),end_time_utc.time()),
                0:(start_time_utc.time(),end_time_utc.time())
                }
        '''
        if we find valid entries in the business_times table for the store id then we 
        input the business hours corresponding to each day of the week.
        ''' 
        for day in schedule:
            start_time_local = day[3]
            end_time_local = day[4]
            today = datetime.now()
            start_datetime = time_zone.localize(datetime.combine(today, start_time_local))
            end_datetime = time_zone.localize(datetime.combine(today, end_time_local))
            start_time_utc = start_datetime.astimezone(utc_tz).time()
            end_time_utc = end_datetime.astimezone(utc_tz).time()
            self.business_hours[day[2]] = (start_time_utc,end_time_utc)
            
    def set_store_status(self,activity):
        '''
        this function takes the readings from store_status table and stores them in a list
        only the readings taken in the business hours of the shop are stored in this list.
        '''
        for reading in activity:
            status = 1 if reading[2]=='active' else 0
            weekday = reading[3].weekday()
            if weekday in self.business_hours :
                date = reading[3].date()

                start_time= self.business_hours[weekday][0]
                end_time = self.business_hours[weekday][1]
                start_date = datetime.combine(date, start_time)

                end_date = datetime.combine(date, end_time) if start_time < end_time else datetime.combine(date + timedelta(days=1), end_time)
                
                
                if start_date<=reading[3] and reading[3]<end_date:
                    self.store_status.append([reading[3],status])

    def check_in_business_time(self,prev_datetime,reading_datetime):
        '''
        check_in_business_time is defined to correctly update the uptime/downtime and handle
        the corner case defined as follows :
        when the status reading is just before the ending of the previous workday and 
        our hold value(prev_datetime to calculate the timedelta) is just after the start
        of a new workday to not count that interval in our uptime/downtime we return false for 
        that interval.
        '''
        delta =  timedelta()+(prev_datetime-reading_datetime)/2
        prev_day= prev_datetime.date()
        reading_day = reading_datetime.date()
        if (prev_day in self.business_hours) and prev_datetime+delta < self.business_hours[prev_day][0] and (reading_day in self.business_hours) and prev_datetime+delta>self.business_hours[reading_day][1]:
            return False
        return True

    def check_in_required_timeframe(self,target_datetime,current_datetime,reading_datetime):
        '''
        this function is used to check if the current reading under consideration is in the 
        time frame asked by the user i.g. last hour, last day or last week. This is done by 
        checking if the current reading is between the two limiting datetimes.
        '''
        if reading_datetime < target_datetime or reading_datetime > current_datetime :
            return False
        return True

    def get_last(self, current_datetime, type):
        '''
        this is the function that finds uptime/downtime simultaneously for specific durations
        depending on the type variable. 
        '''
        uptime = timedelta() 
        downtime = timedelta()
        target_datetime = current_datetime - timedelta(hours=1) 
        if type=="days":
            target_datetime = current_datetime - timedelta(days=1) 
        elif type=="weeks":
            target_datetime = current_datetime - timedelta(weeks=1)
        '''
        in the above code block the target datetime or the get last what(hour/day/week)
        time is found.
        '''

        prev_datetime = current_datetime
        for reading in self.store_status:
            if self.check_in_required_timeframe(target_datetime,current_datetime,reading[0]) and self.check_in_business_time(prev_datetime,reading[0]):
                if reading[1]==1:
                    uptime += prev_datetime - reading[0]    
                else:
                    downtime += prev_datetime - reading[0] 
            else :
                break
            prev_datetime = reading[0]
        '''
        in the above code block the main logic for finding uptime/downtime is implemented.
        so what we are doing here is that we store a prev_datetime variable which is just
        the value of previous reading on store_status list of the class. now once we get to a 
        new reading we see if the current reading represents active or inactive, if the 
        the shop is currently active then we assume that the shop was on from the prev_datetime
        till the current reading, thus add in the uptime, else if the shop is inactive currently
        then assume it was off from the prev_datetime and add in the downtime.
        '''
        
        conversion_factor = 60 if type=="hours" else 3600
        return [uptime.total_seconds() / conversion_factor, downtime.total_seconds() / conversion_factor]


'''
sample data for set_business_hours
[
    (40845, 5955337179846162144, 6, datetime.time(11, 30), datetime.time(21, 30)), 
    (40850, 5955337179846162144, 5, datetime.time(11, 30), datetime.time(21, 30)), 
    (40849, 5955337179846162144, 4, datetime.time(11, 30), datetime.time(21, 30)), 
    (40848, 5955337179846162144, 3, datetime.time(11, 30), datetime.time(21, 30)), 
    (40847, 5955337179846162144, 2, datetime.time(11, 30), datetime.time(21, 30)), 
    (40851, 5955337179846162144, 1, datetime.time(11, 30), datetime.time(21, 30)), 
    (40846, 5955337179846162144, 0, datetime.time(11, 30), datetime.time(21, 30))
]
'''

'''
sample data for set_store_status
[
    (959294, 5955337179846162144, 'active', datetime.datetime(2023, 1, 25, 18, 11, 47, 787759)), (938077, 5955337179846162144, 'active', datetime.datetime(2023, 1, 25, 17, 3, 44, 407218)), (547594, 5955337179846162144, 'active', datetime.datetime(2023, 1, 25, 16, 5, 48, 558023)), (461085, 5955337179846162144, 'active', datetime.datetime(2023, 1, 25, 15, 4, 5, 177461)), 
]
'''