import os
import sys
import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QCheckBox, QMenu, QHBoxLayout, QVBoxLayout,
    QProgressBar, QMessageBox, QGridLayout, QAbstractItemView, QSplitter
)
from PyQt5.QtWidgets import QHeaderView

from musicdl import musicdl
from musicdl.modules.utils.misc import touchdir, sanitize_filepath


# ================= 搜索线程 =================
class SearchThread(QThread):
    result = pyqtSignal(str, list)
    error = pyqtSignal(str, str)

    def __init__(self, source, keyword):
        super().__init__()
        self.source = source
        self.keyword = keyword

    def run(self):
        try:
            client = musicdl.MusicClient(music_sources=[self.source])
            res = client.search(keyword=self.keyword)
            self.result.emit(self.source, res.get(self.source, []))
        except Exception as e:
            self.error.emit(self.source, str(e))


# ================= 下载线程 =================
class DownloadThread(QThread):
    progress = pyqtSignal(int, int)     # task_id, percent
    finished = pyqtSignal(int)
    error = pyqtSignal(int, str)

    def __init__(self, task_id, song_info, music_client):
        super().__init__()
        self.task_id = task_id
        self.song_info = song_info
        self.music_client = music_client

    def run(self):
        try:
            headers = self.music_client.music_clients[
                self.song_info['source']
            ].default_download_headers

            with requests.get(
                self.song_info['download_url'],
                headers=headers,
                stream=True,
                verify=False
            ) as resp:

                if resp.status_code != 200:
                    self.error.emit(self.task_id, "HTTP Error")
                    return

                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                touchdir(self.song_info['work_dir'])
                filename = f"{self.song_info['singers']} - {self.song_info['song_name']}.{self.song_info['ext']}"
                output = sanitize_filepath(
                    os.path.join(self.song_info['work_dir'], filename)
                )

                with open(output, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.emit(
                                self.task_id,
                                int(downloaded / total * 100)
                            )

            self.finished.emit(self.task_id)

        except Exception as e:
            self.error.emit(self.task_id, str(e))


# ================= GUI =================
class MusicdlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicdlGUI")
        self.setFixedSize(1250, 600)

        self.init_data()
        self.init_ui()
        self.bind_events()

    def init_data(self):
        self.music_records = {}
        self.search_threads = []
        self.download_threads = {}
        self.current_row = 0
        self.current_task_id = 0

    def init_ui(self):
        self.sources = [
            'QQMusicClient', 'KuwoMusicClient', 'MiguMusicClient',
            'QianqianMusicClient', 'KugouMusicClient', 'NeteaseMusicClient'
        ]

        self.label_src = QLabel("Search Engine:")
        self.check_boxes = []
        for s in self.sources:
            cb = QCheckBox(s)
            cb.setChecked(True)
            self.check_boxes.append(cb)

        # 资源库（self.sources）一行显示
        sources_layout = QHBoxLayout()  # 横向排列
        sources_layout.addWidget(self.label_src)  # 标签
        for cb in self.check_boxes:  # 每个 checkbox 按顺序排列
            sources_layout.addWidget(cb)

        # 歌名和搜索按钮
        self.label_keyword = QLabel("歌名 (多首歌曲用英文分号;分割):")
        self.lineedit_keyword = QLineEdit("晴天;江南")
        self.button_search = QPushButton("Search")

        # 歌名输入框、按钮换行显示
        keyword_layout = QHBoxLayout()  # 垂直排列
        keyword_layout.addWidget(self.label_keyword)
        keyword_layout.addWidget(self.lineedit_keyword)
        keyword_layout.addWidget(self.button_search)

        # 搜索结果表
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ['ID', 'Singers', 'Song', 'Size', 'Duration', 'Album', 'Source']
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 启用列宽拖拽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 下载任务表
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(
            ["Song", "Source", "Status", "Progress"]
        )
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setAlternatingRowColors(True)

        # 启用下载任务表的列宽拖拽
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.menu = QMenu(self)
        self.action_download = self.menu.addAction("Download")

        # ================= 顶部控件布局 =================
        top_layout = QVBoxLayout()  # 总布局使用垂直方向
        top_layout.addLayout(sources_layout)  # 添加资源库的横向布局
        top_layout.addLayout(keyword_layout)  # 添加歌名和按钮的垂直布局

        # ================= 左右分割布局 =================
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)  # 左侧搜索结果

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("Download Tasks"))
        right_layout.addWidget(self.task_table)
        splitter.addWidget(right_widget)

        # 设置默认宽度比例 2:1
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # ================= 主布局 =================
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)  # 添加顶部控件布局
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def bind_events(self):
        self.button_search.clicked.connect(self.search)
        self.lineedit_keyword.returnPressed.connect(self.search)
        self.table.cellDoubleClicked.connect(self.on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(
            lambda _: self.menu.exec_(QCursor.pos())
        )
        self.action_download.triggered.connect(self.download)

    # ================= 搜索 =================
    def search(self):
        self.init_data()
        self.table.setRowCount(0)
        self.task_table.setRowCount(0)

        keywords = [k.strip() for k in self.lineedit_keyword.text().split(";") if k.strip()]
        sources = [cb.text() for cb in self.check_boxes if cb.isChecked()]

        for kw in keywords:
            for src in sources:
                t = SearchThread(src, kw)
                t.result.connect(self.on_search_result)
                t.error.connect(self.on_search_error)
                self.search_threads.append(t)
                t.start()

    def on_search_result(self, source, results):
        for item in results:
            row = self.current_row
            self.table.insertRow(row)

            values = [
                str(row),
                item['singers'],
                item['song_name'],
                item['file_size'],
                item['duration'],
                item['album'],
                item['source']
            ]

            for col, v in enumerate(values):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, cell)

            self.music_records[str(row)] = item
            self.current_row += 1

    def on_search_error(self, source, msg):
        QMessageBox.warning(self, "Search Error", f"{source}: {msg}")

    # ================= 下载 =================
    def download(self):
        if not self.table.selectedItems():
            return

        row = self.table.selectedItems()[0].row()
        info = self.music_records[str(row)]
        info['work_dir'] = "./downloads"

        task_id = self.current_task_id
        self.current_task_id += 1

        task_row = self.task_table.rowCount()
        self.task_table.insertRow(task_row)
        self.task_table.setItem(task_row, 0, QTableWidgetItem(f"{info['singers']} - {info['song_name']}"))
        self.task_table.setItem(task_row, 1, QTableWidgetItem(info['source']))
        self.task_table.setItem(task_row, 2, QTableWidgetItem("Downloading"))
        self.task_table.setItem(task_row, 3, QTableWidgetItem("0%"))

        client = musicdl.MusicClient(music_sources=[info['source']])
        thread = DownloadThread(task_id, info, client)
        thread.progress.connect(self.on_task_progress)
        thread.finished.connect(self.on_task_finished)
        thread.error.connect(self.on_task_error)

        self.download_threads[task_id] = (thread, task_row)
        thread.start()

    def on_task_progress(self, task_id, percent):
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 3).setText(f"{percent}%")

    def on_task_finished(self, task_id):
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 2).setText("Finished")
        self.task_table.item(row, 3).setText("100%")

    def on_task_error(self, task_id, msg):
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 2).setText("Error")
        self.task_table.item(row, 3).setText(msg)

    def on_double_click(self, row, col):
        self.table.selectRow(row)
        self.download()


# ================= 入口 =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MusicdlGUI()
    gui.show()
    sys.exit(app.exec_())

