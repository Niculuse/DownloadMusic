import os
import sys
import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QCheckBox, QMenu,
    QHBoxLayout, QVBoxLayout, QMessageBox,
    QAbstractItemView, QSplitter
)
from PyQt5.QtWidgets import QHeaderView

from musicdl import musicdl
from musicdl.modules.utils.misc import touchdir, sanitize_filepath


class SearchThread(QThread):
    result = pyqtSignal(int, list)
    error = pyqtSignal(int, str)

    def __init__(self, search_id, source, keyword):
        super().__init__()
        self.search_id = search_id
        self.source = source
        self.keyword = keyword

    def run(self):
        try:
            client = musicdl.MusicClient(music_sources=[self.source])
            res = client.search(keyword=self.keyword)
            self.result.emit(self.search_id, res.get(self.source, []))
        except Exception as e:
            self.error.emit(self.search_id, str(e))

class DownloadThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int)
    error = pyqtSignal(int, str)

    def __init__(self, task_id, song_info):
        super().__init__()
        self.task_id = task_id
        self.song_info = song_info

    def run(self):
        try:
            client = musicdl.MusicClient(music_sources=[self.song_info['source']])
            headers = client.music_clients[
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

class MusicdlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicdlGUI")
        self.setFixedSize(1250, 600)

        self.search_id = 0
        self.search_threads = []

        self.music_records = {}
        self.current_row = 0

        self.download_threads = {}
        self.current_task_id = 0

        self.init_ui()
        self.bind_events()

    def init_ui(self):
        self.sources = [
            'QQMusicClient', 'KuwoMusicClient', 'MiguMusicClient',
            'QianqianMusicClient', 'KugouMusicClient', 'NeteaseMusicClient'
        ]

        self.check_boxes = []
        for s in self.sources:
            cb = QCheckBox(s)
            cb.setChecked(True)
            self.check_boxes.append(cb)

        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Search Engine:"))
        for cb in self.check_boxes:
            src_layout.addWidget(cb)

        self.lineedit_keyword = QLineEdit("晴天;江南")
        self.button_search = QPushButton("Search")

        kw_layout = QHBoxLayout()
        kw_layout.addWidget(QLabel("Keyword:"))
        kw_layout.addWidget(self.lineedit_keyword)
        kw_layout.addWidget(self.button_search)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ['ID', 'Singers', 'Song', 'Size', 'Duration', 'Album', 'Source']
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(
            ["Song", "Source", "Status", "Progress"]
        )
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Download Tasks"))
        right_layout.addWidget(self.task_table)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(src_layout)
        layout.addLayout(kw_layout)
        layout.addWidget(splitter)

    def bind_events(self):
        self.button_search.clicked.connect(self.search)
        self.lineedit_keyword.returnPressed.connect(self.search)
        self.table.cellDoubleClicked.connect(self.download)

    def search(self):
        self.search_id += 1
        current_id = self.search_id

        self.music_records.clear()
        self.current_row = 0
        self.table.setRowCount(0)

        keywords = [k.strip() for k in self.lineedit_keyword.text().split(";") if k.strip()]
        sources = [cb.text() for cb in self.check_boxes if cb.isChecked()]

        for kw in keywords:
            for src in sources:
                t = SearchThread(current_id, src, kw)
                t.result.connect(self.on_search_result)
                t.error.connect(self.on_search_error)
                self.search_threads.append(t)
                t.start()

    def on_search_result(self, search_id, results):
        if search_id != self.search_id:
            return

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
                self.table.setItem(row, col, QTableWidgetItem(v))

            self.music_records[str(row)] = item
            self.current_row += 1

    def on_search_error(self, search_id, msg):
        if search_id != self.search_id:
            return
        QMessageBox.warning(self, "Search Error", msg)

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

        t = DownloadThread(task_id, info)
        t.progress.connect(self.on_task_progress)
        t.finished.connect(self.on_task_finished)
        t.error.connect(self.on_task_error)

        self.download_threads[task_id] = (t, task_row)
        t.start()

    def on_task_progress(self, task_id, percent):
        if task_id not in self.download_threads:
            return
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 3).setText(f"{percent}%")

    def on_task_finished(self, task_id):
        if task_id not in self.download_threads:
            return
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 2).setText("Finished")
        self.task_table.item(row, 3).setText("100%")

    def on_task_error(self, task_id, msg):
        if task_id not in self.download_threads:
            return
        _, row = self.download_threads[task_id]
        self.task_table.item(row, 2).setText("Error")
        self.task_table.item(row, 3).setText(msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MusicdlGUI()
    gui.show()
    sys.exit(app.exec_())
