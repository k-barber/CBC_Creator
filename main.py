CBZ_regex = r"^(?P<Title>.+?)( - c(?P<ChapterNum>\d+))?( \(v(?P<VolumeNum>\d+)\))? - p(?P<Page>\d+(-\d+)?)( \[(?P<ChapterName>.+?)\])?( {(?P<Publisher>.+?)})? ?(?P<Extension>\.\w+)$"
EH_regex = r"^(\((?P<event>.*?)\) )?(\[(?P<publisher>.+?) ?(\((?P<author>.+?)\))?\] )?(?P<title>.+?)([\(\[]|$)"

if False:
    get_icons = get_resources = None

from qt.core import (
    QDialog,
    QMessageBox,
    QVBoxLayout,
    QTextEdit,
    QDialogButtonBox,
    QTextCursor,
)
from calibre.gui2 import error_dialog, info_dialog

from zipfile import ZipFile
import os
import re
from pathlib import Path

configuration_explanation = """#Use the text box to configure which files are placed into which chapters of the CBC file.
#Chapters should be in the format "filename.cbz : chapter name"
#Pages should be formatted with tabs between the original and the new filename "\toriginal_filename\t=>\tnew_filename"
#Example:
#
#001.cbz : Chapter 1 : Departure
#\tRoxy Gets Serious [Departure] 001.jpg\t=>\t001.jpg
#\tRoxy Gets Serious [Departure] 002.jpg\t=>\t002.jpg
#\t. . .
#002.cbz : Chapter 2 : The Town of Rikarisu
#\tRoxy Gets Serious [The Town of Rikarisu] 037.jpg\t=>\t037.jpg
#\tRoxy Gets Serious [The Town of Rikarisu] 038.jpg\t=>\t038.jpg
#\t. . .
"""


def CBZ_Cleaner(string):
    string = string.replace("[dig]", "")
    string = string.replace("[Cover]", "")
    string = string.replace("[Seven Seas]", "")
    string = string.replace("[danke-Empire]", "")
    string = string.replace("{HQ}", "")
    string = string.replace("[Omake]", "")
    string = string.replace("[ToC]", "")
    string = " ".join(string.split())
    return string


def image_filter(name):
    extension = name[name.rfind(".") :].lower()
    return extension in [".png", ".jpg", ".jpeg", ".gif", ".tiff", ".bmp"]


class CBCConverter(QDialog):
    def __init__(self, gui):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.db = gui.current_db

    def create_cbc_file(self, input_file, book_name):
        os.chdir(os.path.dirname(input_file))
        input_zip = ZipFile(input_file)
        files = input_zip.namelist()
        files_list = list(filter(image_filter, files))

        if len(files_list) < 1:
            error_dialog(
                self.gui,
                "Cannot convert CBZ/CB7",
                "No image files in given archive",
                show=True,
            )
            return False

        cleaned_files = list(map(CBZ_Cleaner, files_list))

        if re.match(CBZ_regex, cleaned_files[0]):
            results = list(map(re.compile(CBZ_regex).search, cleaned_files))
            filename = Path(input_file).with_suffix(".cbc")

            chapters = {}
            for index, reg_ex_result in enumerate(results):
                chapter_num = "unnumbered"
                if reg_ex_result and reg_ex_result.group("ChapterNum"):
                    chapter_num = reg_ex_result.group("ChapterNum")
                else:
                    re_result = re.search(
                        r"(c(h?(apter)?)).??(?P<chapter>\d+)", cleaned_files[index]
                    )
                    if re_result and re_result.group("chapter"):
                        chapter_num = re_result.group("chapter")

                chapter_name = ""
                if reg_ex_result and reg_ex_result.group("ChapterName"):
                    chapter_name = reg_ex_result.group("ChapterName")

                page_num = ""
                if reg_ex_result and reg_ex_result.group("Page"):
                    page_num = reg_ex_result.group("Page")
                else:
                    re_result = re.search(
                        r"(p|page|pg).??(?P<page>\d+)", cleaned_files[index]
                    )
                    if re_result and re_result.group("page"):
                        page_num = re_result.group("page")
                    else:
                        page_num = str(index).zfill(3)

                if reg_ex_result and reg_ex_result.group("Extension"):
                    Extension = reg_ex_result.group("Extension")
                else:
                    Extension = re.search(
                        r"(?P<extension>\.\w+$)", cleaned_files[index]
                    ).group("extension")

                if chapter_num and (chapter_num in chapters):
                    chapter = chapters[chapter_num]
                    chapter["pages"].append([files_list[index], page_num + Extension])
                elif chapter_num:
                    chapters[chapter_num] = {}
                    chapter = chapters[chapter_num]
                    chapter["name"] = "Chapter " + chapter_num
                    if chapter_name:
                        chapter["name"] = chapter_name
                    chapter["pages"] = []
                    chapter["pages"].append([files_list[index], page_num + Extension])
                else:
                    continue
        else:
            filename = os.path.basename(os.getcwd()) + ".cbc"
            chapters = {"unnumbered": {"name": "", "pages": []}}
            for file in files_list:
                chapters["unnumbered"]["pages"].append([file, file])

        dialog = QDialog(self.gui)
        dialog.setWindowTitle('Configure Chapters for "' + book_name + '"')
        dialog.resize(1000, 900)
        l = QVBoxLayout()
        dialog.setLayout(l)
        text = QTextEdit()
        text.setAcceptRichText(False)
        text.setTabStopDistance(40)
        text.append(configuration_explanation)
        l.addWidget(text)
        buttonBox = QDialogButtonBox()
        buttonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        l.addWidget(buttonBox)

        if ("unnumbered" in chapters) and (len(chapters) < 2):
            for page in chapters["unnumbered"]["pages"]:
                text.append("\t" + page[0] + "\t=>\t" + page[1])
        else:
            for chapter_num in chapters:
                text.append(
                    chapter_num
                    + ".cbz: Chapter "
                    + chapter_num.lstrip("0")
                    + " : "
                    + chapters[chapter_num]["name"]
                )
                for page in chapters[chapter_num]["pages"]:
                    text.append("\t" + page[0] + "\t=>\t" + page[1])

        cursor = text.textCursor()
        cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor, 1)
        text.setTextCursor(cursor)

        retval = dialog.exec_()
        if retval != QDialog.Accepted:
            print("Not Converted")
            return False

        chapter_config = text.toPlainText()

        cbc_files = []
        comics = open("comics.txt", "w")
        cbc_obj = ZipFile(filename, "w")

        zipObj = None
        for line in chapter_config.split("\n"):
            if line.startswith("\t"):
                split = line.split("\t")
                if zipObj:
                    if input_zip:
                        with zipObj.open(split[3].strip(), "w") as file_in_zip:
                            file_in_zip.write(input_zip.read(split[1].strip()))
                            file_in_zip.close()
                    else:
                        zipObj.write(split[1].strip(), split[3].strip())
                else:
                    if input_zip:
                        with cbc_obj.open(split[3].strip(), "w") as file_in_zip:
                            file_in_zip.write(input_zip.read(split[1].strip()))
                            file_in_zip.close()
                    else:
                        cbc_obj.write(split[1].strip(), split[3].strip())
            elif line.startswith("#"):
                continue
            elif len(line) == 0:
                continue
            else:
                comics.write(line + "\n")
                split = line.split(":")
                if zipObj:
                    zipObj.close()
                zipObj = ZipFile(split[0].strip(), "w")
                cbc_files.append(split[0].strip())
        if zipObj:
            zipObj.close()

        comics.close()

        if len(cbc_files) < 1:
            error_dialog(
                self.gui,
                "Cannot create CBC file",
                "CBC files must contain at least one chapter",
                show=True,
            )
            return False

        cbc_obj.write("comics.txt")
        for file in cbc_files:
            cbc_obj.write(file)

        cbc_obj.close()

        os.remove("comics.txt")
        for file in cbc_files:
            os.remove(file)

        return filename

    def convert_books(self):
        # Get currently selected books
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(
                self.gui, "Cannot convert to CBC", "No books selected", show=True
            )

        # Map the rows to book ids
        ids = list(map(self.gui.library_view.model().id, rows))
        converted = 0
        db = self.db.new_api
        for book_id in ids:

            book_title = db.field_for("title", book_id)

            # Get the CBZ or CB7 file
            if db.has_format(book_id, "cbz"):
                file = db.format(book_id, "cbz", as_path=True)
            elif db.has_format(book_id, "cb7"):
                file = db.format(book_id, "cb7", as_path=True)
            else:
                error_dialog(
                    self.gui,
                    "Cannot convert to CBC",
                    '"' + book_title + '" has no CB7 or CBZ format',
                    show=True,
                )
                continue

            # Convert the CBZ or CB7 file
            cbc = self.create_cbc_file(file, book_title)

            # If the file was successfully converted, add 1 to the counter, and check for overwriting
            if cbc:
                if db.add_format(book_id, "cbc", cbc, replace=False):
                    converted += 1
                else:
                    msg = QMessageBox()
                    msg.setText(
                        'CBC format for "' + book_title + '" already exists, overwrite?'
                    )
                    msg.setWindowTitle("Overwrite Warning")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    retval = msg.exec_()
                    if retval == QMessageBox.Yes:
                        db.add_format(book_id, "cbc", cbc, replace=True)
                        converted += 1

        # Say how many books were successful
        info_dialog(
            self,
            "Updated files",
            "Converted " + str(converted) + " of " + str(len(ids)) + " book(s)",
            show=True,
        )
