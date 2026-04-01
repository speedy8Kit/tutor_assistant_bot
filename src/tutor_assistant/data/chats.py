import pandas as pd


class ChatsInfo(pd.DataFrame):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)


def get_chats_info():
    pass
