# '''
# Author: pang-lee
# Date: 2024-07-11 09:55:48
# LastEditTime: 2024-07-11 09:55:49
# LastEditors: LAPTOP-22MC5HRI
# Description: logger Setting
# FilePath: \openai\template\logger_setting.py
# '''
import os, datetime, shutil, logging
from logging.handlers import TimedRotatingFileHandler

class Logger:
    def __init__(self, name=None, config=None, logs_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/logs'):
        if name is None:
            raise RuntimeError('Logger Name Must Be Specify When Init The Logger.')
        
        self._config = config or {}
        self._logger_name = name
        self._log_dir = logs_dir
        self._logger = self._setup_logger()

    @property
    def logger_name(self):
        return self._logger_name
    
    @logger_name.setter
    def logger_name(self, name):
        self._logger_name = name
        self._logger = self._setup_logger()
    
    @property
    def logs_dir(self):
        return self._logs_dir
    
    @logs_dir.setter
    def logs_dir(self, dir_path):
        self._logs_dir = os.path.abspath(dir_path)
        self._logger = self._setup_logger()
    
    def _setup_logger(self):
        if not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir)

        log_dir_path = os.path.join(self._log_dir, self._logger_name)
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)
        
        logger = logging.getLogger(self._logger_name)
        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir_path, f'{self._logger_name}.log'),
            when=self._config.get('when', 'midnight'),
            interval=self._config.get('interval', 1),
            backupCount=self._config.get('backupCount', 10),
            encoding=self._config.get('encoding', 'utf-8'),
            delay=self._config.get('delay', False),
            utc=self._config.get('utc', False),
            atTime=self._config.get('atTime', None),
            errors=self._config.get('errors', None)
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s on path %(pathname)s at line: %(lineno)d: %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        return logger

    def move_old_logs(self):
        # 查找并处理超过7天的日志文件
        current_date = datetime.datetime.now()
        
        for subfolder in os.listdir(self._log_dir):
            subfolder_path = os.path.join(self._log_dir, subfolder)
            for filename in os.listdir(subfolder_path):
                # 存储旧压缩日志的目录  
                old_logs_path = os.path.join(subfolder_path, 'old')

                if not os.path.exists(old_logs_path):
                    os.makedirs(old_logs_path)

                if not filename.endswith('.log') and filename != 'old':
                    # 提取文件中的时间戳部分
                    try:
                        timestamp_str = filename.split('.log.')
                        file_time = datetime.datetime.strptime(timestamp_str[1], '%Y-%m-%d')
                        date_str = f"{timestamp_str[0]}-{file_time}"
                        new_dir_path = os.path.join(old_logs_path, date_str)
                        if not os.path.exists(new_dir_path):
                            os.makedirs(new_dir_path)
                    except (IndexError, ValueError):
                        # 如果无法解析时间戳，则跳过该文件
                        raise RuntimeError(f'Cannot Parse The File Time At class Logger with {filename}')
                    
                    # 计算文件时间与当前时间的差值
                    time_diff = current_date - file_time
                    if time_diff > datetime.timedelta(days=7):
                        # 将旧文件移动到 old 目录
                        src_path = os.path.join(self._log_dir, subfolder_path, filename)
                        shutil.move(src_path, os.path.join(new_dir_path, os.path.basename(filename)))

    def get_logger(self):
        return self._logger