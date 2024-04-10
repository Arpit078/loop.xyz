    from fastapi import FastAPI, BackgroundTasks,Depends
    from fastapi.responses import FileResponse
    from sqlalchemy import create_engine, Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy import DateTime
    from fastapi.responses import StreamingResponse
    from sqlalchemy import text
    import pytz
    from datetime import datetime
    from store import Store
    import time 
    import csv
    import random
    import string
    import json
utc_tz = pytz.UTC
current_time_stamp = "2023-01-25 18:13:22.47922"
current_datetime = datetime.strptime(current_time_stamp, '%Y-%m-%d %H:%M:%S.%f')
database_url = "postgresql://postgres:root@localhost/loop"

engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def process_csv(filename,db):
    query_result = db.execute(text(f"SELECT * FROM time_zone"))
    time_zone_rows = query_result.fetchall()
    with open("./reports/"+filename+".csv", 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['store_id', 'uptime_last_hour(in minutes)', 'uptime_last_day(in hours)','update_last_week(in hours)','downtime_last_hour(in minutes)','downtime_last_day(in hours)','downtime_last_week(in hours)'])
        for id,store_id,time_zone in time_zone_rows:
            query_result = db.execute(text(f"SELECT * FROM store_times WHERE store_id={store_id} ORDER BY day DESC"))
            business_hours_rows = query_result.fetchall()
            store = Store(store_id,time_zone)
            store.set_business_hours(business_hours_rows)
            query_result = db.execute(text(f"SELECT * FROM store_status WHERE store_id={store_id} ORDER BY time_stamp_utc DESC"))
            store_status_rows = query_result.fetchall()
            store.set_store_status(store_status_rows)
          
            [uptime_last_hour,downtime_last_hour]= store.get_last(current_datetime,'hours')
            [uptime_last_day,downtime_last_day] = store.get_last(current_datetime,'days')
            [uptime_last_week,downtime_last_week] = store.get_last(current_datetime,'weeks')

            csvwriter.writerow([store.store_id,uptime_last_hour,uptime_last_day,uptime_last_week,downtime_last_hour,downtime_last_day,downtime_last_week])
            del store
    with open('report_gen_map.json', 'r+') as file:
        content = file.read()
        data = json.loads(content)
        data[f"{filename}"] = 0
        file.seek(0)
        file.truncate()
        json.dump(data, file)
        file.flush()


def generate_random_string(length):
    letters = string.ascii_letters
    random_string = ''.join(random.choice(letters) for i in range(length))
    return random_string
@app.get("/trigger_report")
async def trigger_report(background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    filename = generate_random_string(10)
    with open("report_gen_map.json",'r+') as file:
        content = file.read()
        data = json.loads(content)
        data.update({f"{filename}": 1})
        file.seek(0)
        file.truncate()
        json.dump(data, file)
        file.flush()
    background_tasks.add_task(process_csv,filename,db)
    return filename

@app.get("/get_report/{filename}")
async def get_report(filename):
    with open('report_gen_map.json', 'r+') as file:
        content = file.read()
        data = json.loads(content)
        if data[f"{filename}"]==1:
            return "Running"
        else:
             del data[f"{filename}"]
             return FileResponse("./reports/"+filename+".csv", media_type='text/csv',filename=filename+".csv")
        file.seek(0)
        file.truncate()
        json.dump(data, file)
        file.flush()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
