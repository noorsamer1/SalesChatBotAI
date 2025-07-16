import sqlalchemy
engine = sqlalchemy.create_engine('postgresql+psycopg2://chatbot_user:AsdZxc%40123@localhost:5432/chatbot_data')
conn = engine.connect()
print("Success!")
conn.close()