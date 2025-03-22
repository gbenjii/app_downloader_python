import os
import shutil
import requests
import zipfile
import io
import subprocess
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from threading import Thread
import logging
import time


logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class AppUpdater(tk.Tk):
    def __init__(self, source_url, destination_path, main_script, version_url, parancsikon_nev):
        super().__init__()
        self.source_url = source_url
        self.destination_path = destination_path
        self.main_script = main_script
        self.version_url = version_url
        self.parancsikon_nev = parancsikon_nev
        self.download_thread = None
        self.cancel_download = False
        self.start_time = 0

        self.title("Alkalmazásfrissítés")
        self.geometry("400x300")

        self.version_label = ttk.Label(self, text="Verzió: Ismeretlen")
        self.version_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=380, mode="determinate")
        self.progress_bar.pack(pady=5)

        self.status_label = ttk.Label(self, text="Frissítés folyamatban...")
        self.status_label.pack()

        self.cancel_button = ttk.Button(self, text="Mégse", command=self.cancel)
        self.cancel_button.pack(pady=5)

        self.download_thread = Thread(target=self.update_application)
        self.download_thread.start()

        self.get_version()

    def get_version(self):
        try:
            response = requests.get(self.version_url)
            response.raise_for_status()
            version = response.text.strip()
            self.version_label.config(text=f"Verzió: {version}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Verzió lekérési hiba: {e}")

    def update_application(self):
        try:

            self.delete_shortcut()

            if os.path.exists(self.destination_path):
                for item in os.listdir(self.destination_path):
                    item_path = os.path.join(self.destination_path, item)
                    if os.path.isdir(item_path) and item == "save":
                        continue
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            else:
                os.makedirs(self.destination_path)

            self.start_time = time.time()
            response = requests.get(self.source_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            temp_zip_path = os.path.join(self.destination_path, "temp.zip")

            with open(temp_zip_path, "wb") as f:
                for data in response.iter_content(chunk_size=8192):
                    if self.cancel_download:
                        shutil.rmtree(self.destination_path)
                        self.status_label.config(text="Frissítés megszakítva.")
                        self.cancel_button.config(state="disabled")
                        return

                    f.write(data)
                    downloaded_size += len(data)
                    if total_size > 0:
                        self.progress_bar["value"] = (downloaded_size / total_size) * 100
                    else:
                        self.progress_bar["value"] = 0

            if os.path.getsize(temp_zip_path) > 0:
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.destination_path)
                os.remove(temp_zip_path)
            else:
                raise Exception("Üres zip fájl letöltve")

            version = requests.get(self.version_url).text.strip()
            with open(os.path.join(self.destination_path, "version.txt"), "w") as f:
                f.write(version)

            self.create_shortcut()

            self.status_label.config(text="Frissítés kész.")
            self.cancel_button.config(state="disabled")

            if messagebox.askyesno("Alkalmazás megnyitása", "Szeretnéd megnyitni az alkalmazást?"):
                script_path = os.path.join(self.destination_path, self.main_script)
                subprocess.Popen([script_path])
                self.destroy()
            else:
                self.destroy()

        except requests.exceptions.RequestException as e:
            self.status_label.config(text=f"Hiba: {str(e)}")
            self.cancel_button.config(state="disabled")
            logging.error(str(e))
        except zipfile.BadZipFile:
            self.status_label.config(text="Hibás zip fájl.")
            self.cancel_button.config(state="disabled")
            logging.error("Hibás zip fájl.")
        except FileNotFoundError:
            self.status_label.config(text=f"Nem található: {self.main_script}")
            self.cancel_button.config(state="disabled")
            logging.error(f"Nem található fájl: {self.main_script}")
        except Exception as e:
            self.status_label.config(text=f"Váratlan hiba: {str(e)}")
            self.cancel_button.config(state="disabled")
            logging.error(str(e))
        finally:
            if self.download_thread is not None and self.download_thread.is_alive():
                self.download_thread.join()

    def create_shortcut(self):
        try:
            parancsikon_nev = requests.get(self.parancsikon_nev).text.strip()
            shortcut_path = os.path.join(os.path.expanduser("~"), "Desktop", f"{parancsikon_nev}.lnk")
            target = os.path.join(self.destination_path, self.main_script)

            import winshell
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = target
                shortcut.working_directory = self.destination_path

        except requests.exceptions.RequestException as e:
            logging.error(f"Shortcut név lekérési hiba: {e}")
        except Exception as e:
            logging.error(f"Shortcut létrehozási hiba: {e}")

    def delete_shortcut(self):
        try:
            parancsikon_nev = requests.get(self.shortcut_url).text.strip()
            shortcut_path = os.path.join(os.path.expanduser("~"), "Desktop", f"{parancsikon_nev}.lnk")
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                print("Parancsikon törölve.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Shortcut név lekérési hiba: {e}")
        except Exception as e:
            logging.error(f"Parancsikon törlési hiba: {e}")

    def cancel(self):
        self.cancel_download = True

if __name__ == "__main__":
    source_url = "" #zip fájl letöltési helye
    destination_path = "" #letöltés helye
    main_script = "app.exe"
    version_url = "" #verziólekérés txt
    parancsikon_nev = "" #parancsikon_neve txt

    app = AppUpdater(source_url, destination_path, main_script, version_url, parancsikon_nev)
    app.mainloop()
