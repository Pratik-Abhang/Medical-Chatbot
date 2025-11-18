from sqlalchemy import create_engine, text

def get_mysql_engine():
    USER = "root"
    PASSWORD = "PratikAbhang@30"
    HOST = "localhost"   # remote or localhost
    PORT = 3306
    DB = "medical_chatbot"

    url = f"mysql+mysqlconnector://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"
    engine = create_engine(url)
    return engine
