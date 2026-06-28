"""初始化数据库（创建表）。"""
from backend.database.connection import engine, Base


def init_db():
    """根据 models.py 里的模型创建所有表。"""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
