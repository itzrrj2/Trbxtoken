import os

#Database 
#Database [https://youtu.be/qFB0cFqiyOM?si=fVicsCcRSmpuja1A]
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://cphdlust:cphdlust@cphdlust.ydeyw.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DATABASE_NAME", "cphdlust")

#Shortner (token system) 
# check my discription to help by using my refer link of shareus.io


SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "shortner.in")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "6fd47c5091eb04ef85f668af5fabe5c72b0c89c4")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 43200)) # Add time in seconds
IS_VERIFY = os.environ.get("IS_VERIFY", "True")
TUT_VID = os.environ.get("TUT_VID", "https://your.itz-ashlynn.workers.dev/?start=MzA2OTMxOTgxMzI2MzkwOTAwLzczMTI4MjAxNg&bot=AR_File_To_Link_Bot") # shareus ka tut_vid he 
