"""
LinkedIn Auto Apply GUI — Modern Edition
-----------------------------------------
Built by Sci. Abhinandan Yadav (Bio-Silicon Valley)
Python 3.8+ compatible; styled using ttkbootstrap
"""

import os
import csv
import json
import time
import random
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from webdriver_manager.chrome import ChromeDriverManager
import ttkbootstrap as tb


# -------------------------------
# Utility functions
# -------------------------------
def human_sleep(a=1.0, b=3.0):
    time.sleep(random.uniform(a, b))

def js_click(driver, element):
    driver.execute_script("arguments[0].click();", element)

def safe_click(driver, element):
    for _ in range(3):
        try:
            element.click()
            return
        except Exception:
            try:
                ActionChains(driver).move_to_element(element).perform()
                human_sleep(0.2, 0.6)
                element.click()
                return
            except Exception:
                try:
                    js_click(driver, element)
                    return
                except Exception:
                    human_sleep(0.5, 1)
                    continue

def load_form_memory():
    if os.path.exists("form_memory.json"):
        with open("form_memory.json", "r") as f:
            return json.load(f)
    return {}

def save_form_memory(memory):
    with open("form_memory.json", "w") as f:
        json.dump(memory, f, indent=4)

def handle_discard_popup(driver):
    try:
        discard_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Discard')]"))
        )
        print("⚙️ Discard popup detected — choosing Discard.")
        safe_click(driver, discard_btn)
        human_sleep(1, 2)
    except TimeoutException:
        pass

def wait_for_security_check(driver, timeout=600):
    """
    Wait if LinkedIn triggers a security check page after login.
    The function pauses until the user completes it manually.
    """
    start_time = time.time()
    while True:
        current_url = driver.current_url
        if any(x in current_url for x in ["/checkpoint/", "/security-verification"]):
            print("⚠️ Security check detected — please complete manually in browser.")
            print("⏳ Waiting... The script will resume once verification is cleared.")
            time.sleep(5)
            if time.time() - start_time > timeout:
                print("❌ Timeout: Security check not cleared in time.")
                break
        elif "feed" in current_url or "linkedin.com/jobs" in current_url:
            print("✅ Security check cleared. Continuing automation.")
            break
        else:
            time.sleep(3)


# -------------------------------
# Core Automation
# -------------------------------
def run_automation(email, password, keywords, location, headless=False, cap_jobs=100):
    print("🚀 Starting LinkedIn automation...")
    csv_file = "applied_jobs.csv"
    applied_jobs = set()
    if os.path.exists(csv_file):
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    applied_jobs.add(row[0])

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 15)

    total_applied = 0
    page_offset = 0
    max_processed = 0

    try:
        driver.get("https://www.linkedin.com/login")
        human_sleep(2, 4)
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        human_sleep(3, 6)
        print("✅ Login submitted. Checking for security verification...")
        wait_for_security_check(driver)
        print("✅ Proceeding to job search.")


        base_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location}&f_AL=true"
        while True:
            if max_processed >= cap_jobs:
                print(f"Reached cap of {cap_jobs} jobs — stopping.")
                break

            driver.get(f"{base_url}&start={page_offset}")
            human_sleep(3, 5)

            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job-card-container")
            if not job_cards:
                print("⚙️ No more jobs found.")
                break

            for job in job_cards:
                try:
                    if max_processed >= cap_jobs:
                        break
                    try:
                        # Re-locate job element to avoid stale reference
                        job_cards_refreshed = driver.find_elements(By.CSS_SELECTOR, "div.job-card-container")
                        job = job_cards_refreshed[job_cards.index(job)]
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", job)
                        human_sleep(0.8, 1.3)
                        safe_click(driver, job)
                    except StaleElementReferenceException:
                        print("♻️ Job card refreshed — reloading list.")
                        continue

                    human_sleep(0.8, 1.3)
                    safe_click(driver, job)
                    human_sleep(2, 3)

                    link_el = job.find_element(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
                    job_link = link_el.get_attribute("href")
                    job_title = link_el.text.strip()
                    if not job_link or job_link in applied_jobs:
                        continue
                    max_processed += 1

                    try:
                        apply_btn = WebDriverWait(driver, 8).until(
                            EC.element_to_be_clickable((
                                By.XPATH, "//button[contains(.,'Easy Apply')]"
                            ))
                        )
                        print(f"[{max_processed}] 🟢 Easy Apply for: {job_title}")
                        safe_click(driver, apply_btn)
                        # 🚫 Detect LinkedIn Easy Apply limit popup
                        page_source = driver.page_source
                        if "You’ve reached today's Easy Apply limit" in page_source or \
                           "Easy Apply limit" in page_source or \
                           "We limit daily submissions" in page_source:
                            print("🚫 LinkedIn Easy Apply daily limit reached! Stopping automation safely.")
                            try:
                                driver.quit()
                            except Exception:
                                pass

                            try:
                                import tkinter.messagebox as messagebox
                                messagebox.showwarning(
                                    "Daily Limit Reached",
                                    "You've reached LinkedIn’s Easy Apply daily limit.\n"
                                    "Please continue tomorrow."
                                )
                            except Exception:
                                print("⚠️ GUI messagebox not available.")
                            return

                        human_sleep(2, 3)
                    except TimeoutException:
                        print(f"[{max_processed}] 🔸 No Easy Apply for {job_title}")
                        continue

                    try:
                        modal = WebDriverWait(driver, 6).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@role,'dialog')]"))
                        )
                        try:
                            submit_btn = modal.find_element(By.XPATH, ".//button[contains(., 'Submit')]")
                            safe_click(driver, submit_btn)
                            print(f"✅ Applied to {job_title}")
                        except NoSuchElementException:
                            print(f"⚙️ Multi-step form detected for: {job_title}")
                            btns = modal.find_elements(By.XPATH, ".//button[contains(.,'Next') or contains(.,'Submit')]")
                            for b in btns:
                                safe_click(driver, b)
                                human_sleep(2, 3)
                        WebDriverWait(driver, 10).until_not(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@role,'dialog')]"))
                        )
                        applied_jobs.add(job_link)
                        with open(csv_file, "a", newline="", encoding="utf-8") as f:
                            csv.writer(f).writerow([job_link, job_title])
                        total_applied += 1
                    except Exception as e:
                        print(f"❌ Error submitting: {e}")

                except Exception as e:
                    print(f"⚠️ Error handling job: {e}")

            page_offset += 25
            print(f"➡️ Next page offset={page_offset}")

        print(f"🎯 Done! Total applied: {total_applied}")

    except Exception as e:
        print("Fatal error:", e)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# -------------------------------
# GUI Section
# -------------------------------
class TextRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
    def write(self, msg):
        if msg:
            def append():
                self.text_widget.insert("end", msg)
                self.text_widget.see("end")
            self.text_widget.after(0, append)
    def flush(self): pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("LinkedIn Easy Apply - Bio-Silicon Valley Edition")
        root.geometry("1000x700")
        style = tb.Style("cyborg")  # Modern dark theme

        main = ttk.Frame(root, padding=10)
        main.pack(fill="both", expand=True)

        # Logo
        if os.path.exists("logo.png"):
            img = Image.open("logo.png").resize((100, 100))
            self.logo_img = ImageTk.PhotoImage(img)
            logo_lbl = ttk.Label(main, image=self.logo_img)
            logo_lbl.pack(pady=(10, 5))
        ttk.Label(main, text="LinkedIn Auto Apply", font=("Helvetica", 20, "bold")).pack()

        # Form
        form = ttk.Frame(main)
        form.pack(pady=10)

        self.email = tb.Entry(form, width=40)
        self.password = tb.Entry(form, show="*", width=40)
        self.keywords = tb.Entry(form, width=40)
        self.location = tb.Entry(form, width=40)
        self.headless = tk.BooleanVar(value=False)
        self.cap = tb.Entry(form, width=10)
        self.cap.insert(0, "50")

        tb.Label(form, text="LinkedIn Email:").grid(row=0, column=0, sticky="w")
        self.email.grid(row=0, column=1)
        tb.Label(form, text="Password:").grid(row=1, column=0, sticky="w")
        self.password.grid(row=1, column=1)
        tb.Label(form, text="Keywords:").grid(row=2, column=0, sticky="w")
        self.keywords.insert(0, "bioinformatics scientist")
        self.keywords.grid(row=2, column=1)
        tb.Label(form, text="Location:").grid(row=3, column=0, sticky="w")
        self.location.insert(0, "India")
        self.location.grid(row=3, column=1)
        tb.Checkbutton(form, text="Run headless", variable=self.headless).grid(row=4, column=1, sticky="w")
        tb.Label(form, text="Max jobs:").grid(row=5, column=0, sticky="w")
        self.cap.grid(row=5, column=1, sticky="w")

        # Buttons
        btns = ttk.Frame(main)
        btns.pack(pady=10)
        tb.Button(btns, text="Start", bootstyle="success-outline", command=self.start).pack(side="left", padx=5)
        tb.Button(btns, text="Stop", bootstyle="danger-outline", command=self.stop).pack(side="left", padx=5)
        tb.Button(btns, text="Open CSV", bootstyle="info-outline", command=self.open_csv).pack(side="left", padx=5)

        # Console
        tb.Label(main, text="Console Output:").pack(anchor="w")
        self.log = tk.Text(main, wrap="word", height=20, bg="#000", fg="#00ff99", insertbackground="white")
        self.log.pack(fill="both", expand=True)
        sys.stdout = TextRedirector(self.log)
        sys.stderr = TextRedirector(self.log)
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            messagebox.showinfo("Info", "Automation already running.")
            return
        email = self.email.get().strip()
        password = self.password.get().strip()
        keywords = self.keywords.get().strip()
        location = self.location.get().strip()
        cap_jobs = int(self.cap.get() or 50)
        if not email or not password:
            messagebox.showerror("Error", "Please enter LinkedIn email and password.")
            return
        self.thread = threading.Thread(target=run_automation,
            args=(email, password, keywords, location, self.headless.get(), cap_jobs),
            daemon=True)
        self.thread.start()

    def stop(self):
        messagebox.showinfo("Stop", "Please close Chrome manually to stop automation safely.")

    def open_csv(self):
        path = os.path.abspath("applied_jobs.csv")
        if os.path.exists(path):
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                os.system(f"xdg-open '{path}'")
        else:
            messagebox.showinfo("Info", "No applied_jobs.csv found yet.")


if __name__ == "__main__":
    root = tb.Window(themename="cyborg")
    app = App(root)
    root.mainloop()

