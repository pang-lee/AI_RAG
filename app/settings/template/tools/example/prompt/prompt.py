chatbot_name = 'get_menu_vectorstore_data'
chatbot_description = '''
        當詢問菜單, Menu, 點菜, 菜單選項, 餐牌或與菜單相關關鍵字時, 解析出想詢問的內容做為query,
        並使用此Tools來查詢菜單向量庫(db={db})資料.
        reply:
        根據詢問的菜單相關訊息, (數字序列顯示)查詢結果
    '''