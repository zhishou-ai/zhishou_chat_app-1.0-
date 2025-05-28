import sys
from PyQt6 import QtCore, QtGui, QtWidgets


from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal

class ChangeNicknameWindow(QtWidgets.QMainWindow):
    nickname_changed = pyqtSignal(str)  # 昵称更改时发射的信号
    
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # 连接确定按钮的点击事件
        self.ui.pushButton_2.clicked.connect(self.change_nickname)

    def change_nickname(self):
        """更改昵称"""
        new_nickname = self.ui.textEdit.toPlainText().strip()
        if not new_nickname:
            QtWidgets.QMessageBox.warning(self, "警告", "请输入新昵称")
            return
            
        # 发射昵称更改信号
        self.nickname_changed.emit(new_nickname)
        self.close()


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(607, 396)

        # 中央部件
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # 昵称输入框
        self.textEdit = QtWidgets.QTextEdit(parent=self.centralwidget)
        self.textEdit.setGeometry(QtCore.QRect(380, 60, 151, 41))
        self.textEdit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #CCCCCC;
                border-radius: 10px;
                padding: 2px;
                background-color: rgba(0, 0, 0, 80);
                color: white;
                font-family: "宋体";
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.textEdit.setObjectName("textEdit")

        # 确定按钮
        self.pushButton_2 = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(390, 140, 141, 31))
        self.pushButton_2.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(0, 0, 0, 10);
                color: black;
                padding: 5px 10px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: transparent;
                border-color: rgba(0, 0, 0, 20);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 20);
                border-color: rgba(0, 0, 0, 30);
                color: black;
            }
            QPushButton:disabled {
                color: rgba(0, 0, 0, 30);
                border-color: rgba(0, 0, 0, 5);
            }
        """)
        self.pushButton_2.setObjectName("pushButton_2")

        # 标签
        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(430, 20, 54, 16))
        self.label.setObjectName("label")

        MainWindow.setCentralWidget(self.centralwidget)

        # 菜单栏和状态栏
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 607, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "更改昵称"))
        self.pushButton_2.setText(_translate("MainWindow", "确定"))
        self.label.setText(_translate("MainWindow", "输入昵称"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # 设置全局字体
    font = QtGui.QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = ChangeNicknameWindow()
    window.show()
    sys.exit(app.exec())