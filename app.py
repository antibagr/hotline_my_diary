import os
import sys
from datetime import timedelta, datetime, date
import datetime as dt_module


import logging
import sqlite3

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt

from typing import List, Tuple, Union, Optional, Dict

Ui_MainWindow, _ = uic.loadUiType("calendar.ui")


class Helper():
    """Wrapper class for functions neither related to design nor to database"""

    def GetMonthDays(d: Optional[Union[datetime, datetime.date]] = None) -> List[datetime.date]:
        """Author of the code:
            https://stackoverflow.com/users/10337630/sentence
        Args:
            d: Optional[Union[datetime, datetime.date]] = None # target date / datetime object
        Returns:
            List[datetime.date]: list of all days in current month
        """

        d = d if d else datetime.now()

        current_month = d.month
        current_year = d.year
        days_delta = (date(current_year, current_month + 1, 1) - date(current_year, current_month, 1)).days
        start_day = date(current_year, current_month, 1)
        end_day = date(current_year, current_month, days_delta)
        month_delta = end_day - start_day

        return [(start_day + timedelta(days=day)) for day in range(month_delta.days + 1)]

    def FirstAndLastDayOfMonth(d: Union[datetime, datetime.date]) -> Tuple[datetime.date, datetime.date]:
        """ Author of the original code:
            https://stackoverflow.com/users/317971/augustomen
        Args:
            d: Union[datetime, datetime.date] # any date / datetime of a target month
        Returns:
            Tuple[datetime.date, datetime.date] # first and last day of month
        """

        d = d.date() if not isinstance(d, dt_module.date) else d

        last_day = d.replace(month=d.month + 1 if d.month < 12 else 1, day=1) - timedelta(days=1)

        first_day = d.replace(day=1)

        return (first_day.date(), last_day.date())


DataBaseCheckBox = Tuple[int, int, int, str]

class Database():

    tablename: str = 'checkboxes'

    DB_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), 'db.db'))

    def __init__(self) -> None:

        self.connection = sqlite3.connect(self.DB_PATH)
        logging.info("Successfully connect to database")
        self.create_table()
        self.initiate_month()
        logging.info("Successfully load environment")

    def create_table(self) -> None:

        cursor: sqlite3.cursor = self.connection.cursor()

        # cursor.execute(f'drop table {self.tablename}')

        cursor.execute(f"create table if not exists {self.tablename} (id integer primary key AUTOINCREMENT, checked boolean, day integer, month integer, full_date date)")

    def initiate_month(self) -> None:
        """Checks if days of the current month are
            inserted into database already.
            Inserts them if cannot find.
        """

        today = datetime.now()

        cursor: sqlite3.Cursor = self.connection.cursor()
        stored_days_list = self.get_checkboxes( today, cursor=cursor)

        if not stored_days_list:

            insert_line = f'insert into {self.tablename} (id, checked, day, month, full_date) values(?, ?, ?, ?, ?)'
            today = today.date()
            days_list = Helper.GetMonthDays()
            cursor.executemany(insert_line, ((None, day < today, day.day, day.month, day) for day in days_list))
            self.connection.commit()
            logging.info(f'Have inserted {cursor.rowcount} records to the table.')

    def get_checkboxes(self, d: Union[datetime, datetime.date], cursor: Optional[sqlite3.Cursor] = None) -> List[DataBaseCheckBox]:
        cursor = cursor or self.connection.cursor()
        days_list = cursor.execute(f"SELECT * from {self.tablename} where month = ?", (d.month, )).fetchall()
        return days_list

    def save_changes(self, boxes: Dict[int, QtWidgets.QCheckBox]):

        cursor: sqlite3.Cursor = self.connection.cursor()
        month = datetime.now().month
        cursor.executemany(f'update {self.tablename} set checked = ? where day = ? and month = ?', ((box.isChecked(), index, month) for index, box in boxes.items()))
        self.connection.commit()


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    boxes: Dict[int, QtWidgets.QCheckBox]
    size: int
    database: Database

    def __init__(self) -> None:

        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.database = Database()

        logging.info("Successfully create main window")

        self.boxes = {index: getattr(self, f'checkBox_{index}') for index in range(1, 32) }

        self.size = len(self.boxes)
        _, last_d = Helper.FirstAndLastDayOfMonth(datetime.now())
        self.days_in_month: int = int(last_d.day)

        self.connect_checkboxes()

    def setup_design(self) -> None:
        self.setWindowTitle(f"Hot-line my dairy")

        self.month.setText(datetime.now().strftime('%B'))
        self.month.setToolTip("Mark checkbox when you've done your daily routine. Let's gear it!")

    def connect_checkboxes(self) -> None:

        stored_days_list = {item[0]: item[1:] for item in self.database.get_checkboxes( datetime.now() )[::-1] }

        for index, checkbox in self.boxes.items():
            if index > self.days_in_month:
                checkbox.hide()

        for index, item in stored_days_list.items():
            checkbox: QtWidgets.QCheckBox = self.boxes[index]
            checkbox.stateChanged.connect(lambda state, index = index: self.state_changed(state, index))

            checkbox.setChecked(stored_days_list[index][0])
            checkbox.setToolTip(stored_days_list[index][-1])
            if index > 1:
                checkbox.setEnabled(stored_days_list[index][0])

    def state_changed(self, state: int, index: int):

        print(f'{index} => {bool(state)}')

        if state:

            try:
                if index + 1 > self.days_in_month:
                    raise KeyError('Next month switch')

                next_checkbox: QtWidgets.QCheckBox = self.boxes[index + 1]
                next_checkbox.setEnabled(True)
                # self.database.update_checked(index, state)

            except KeyError:
                self.boxes[1].setChecked(False)

        else:

            # self.database.update_checked(index, state)

            for i in range(index, self.size + 1):
                checkbox: QtWidgets.QCheckBox = self.boxes[i]
                if checkbox.isChecked():
                    checkbox.setChecked(False)
                if i > index:
                    checkbox.setEnabled(False)

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.hide()
        self.database.save_changes(self.boxes)

        super().closeEvent(event)


if __name__ == '__main__':

    # Entry point

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
