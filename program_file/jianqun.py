import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSignal

class CreateGroupWindow(QtWidgets.QMainWindow):
    group_created = pyqtSignal(str, list)  # 建群成功时发射的信号
    
    def __init__(self, online_users=None):
        super().__init__()
        self.online_users = online_users or []
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # 添加在线用户到列表
        for user in self.online_users:
            item = QtWidgets.QListWidgetItem(user)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.ui.listWidget.addItem(item)
        
        # 连接创建群聊按钮的点击事件
        self.ui.jianqun.clicked.connect(self.create_group)

    def create_group(self):
        """创建群组"""
        group_name = self.ui.shurukuang.toPlainText().strip()
        if not group_name:
            QtWidgets.QMessageBox.warning(self, "警告", "请输入群聊名称")
            return
            
        # 获取选中的成员
        members = []
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                members.append(item.text())
        
        # 发射建群信号
        self.group_created.emit(group_name, members)
        self.close()


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(488, 460)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # 列表控件
        self.listWidget = QtWidgets.QListWidget(parent=self.centralwidget)
        self.listWidget.setGeometry(QtCore.QRect(0, 0, 491, 281))
        self.listWidget.setStyleSheet("""
            QListWidget {
                outline: 0;
                border: none;
                background-color: rgba(0, 0, 0, 0);
                border-radius: 10px;
                padding: 2px;
            }
            QListWidget::item {
                height: 50px;
                padding: 0 15px;
                border: none;
                border-radius: 0;
                margin: 0;
                background-color: rgba(50, 50, 50, 70);
                color: white;
                font-family: "宋体";
                font-size: 18px;
                font-weight: bold;
                border-bottom: 2px solid rgba(30, 30, 30, 90);
            }
            QListWidget::item:first {
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QListWidget::item:last {
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }
            QListWidget::item:hover {
                background-color: rgba(70, 70, 70, 100);
                border-bottom-color: rgba(50, 50, 50, 120);
            }
            QListWidget::item:selected {
                background-color: rgba(90, 90, 90, 150);
                border-bottom-color: rgba(70, 70, 70, 170);
                color: white;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0);
                width: 12px;
                margin: 10px 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 60);
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
                border: none;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(180, 180, 180, 60);
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical,
            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                background: transparent;
            }
            QListWidget::item::icon {
                margin-left: 10px;
                margin-right: 15px;
            }
        """)
        self.listWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.listWidget.setObjectName("listWidget")


        # 创建群聊按钮
        self.jianqun = QtWidgets.QPushButton(parent=self.centralwidget)
        self.jianqun.setGeometry(QtCore.QRect(80, 360, 321, 41))
        self.jianqun.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                padding: 15px 20px 5px 20px;
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
        self.jianqun.setObjectName("jianqun")

        # 输入框
        self.shurukuang = QtWidgets.QTextEdit(parent=self.centralwidget)
        self.shurukuang.setGeometry(QtCore.QRect(80, 270, 331, 41))
        self.shurukuang.setStyleSheet("")
        self.shurukuang.setObjectName("shurukuang")

        # 标签
        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(210, 230, 71, 21))
        self.label.setObjectName("label")

        MainWindow.setCentralWidget(self.centralwidget)

        # 菜单栏和状态栏
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 488, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "创建群聊"))
        self.jianqun.setText(_translate("MainWindow", "创建群聊"))
        self.label.setText(_translate("MainWindow", "群聊名称"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # 设置全局字体
    font = QtGui.QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = CreateGroupWindow()
    window.show()
    sys.exit(app.exec())