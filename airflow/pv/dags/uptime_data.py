from airflow.sdk import DAG, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timezone, timedelta
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import json

URL = "https://ff14fish.carbuncleplushy.com/"
VIEWPORT = (1400, 1000)
CLICK_SLEEP = 0.3
KST = timezone(timedelta(hours=9))

def extract_modal_data_selenium(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal.upcoming-windows.active .upcoming-windows-grid"))
        )
        root = driver.find_element(By.CSS_SELECTOR, ".modal.upcoming-windows.active .upcoming-windows-grid")
        starts = root.find_elements(By.CSS_SELECTOR, ".window-start")
        durations = root.find_elements(By.CSS_SELECTOR, ".window-duration")
        data = []
        for i in range(len(starts)):
            data.append({
                "start": starts[i].text.strip(),
                "duration": durations[i].text.strip()
            })
        return data
    except Exception as e:
        return {"error": str(e)}

def handle_new_fish_modal(driver, timeout=3):
    """
    'New Fish Available' 모달이 있을 때만 'Yes'를 눌러 닫는다.
    없으면 조용히 패스.
    """
    try:
        wait = WebDriverWait(driver, timeout, poll_frequency=0.25)
        # 모달이 DOM에 있고 보여질 때까지 대기
        modal = wait.until(EC.visibility_of_element_located((By.ID, "new-fish-available-modal")))
        # 모달 안의 Yes 버튼 찾기
        yes_btn = modal.find_element(By.ID, "show-the-new-fishies")
        try:
            yes_btn.click()
        except ElementClickInterceptedException:
            # 오버레이/애니메이션 등으로 클릭 막히면 JS로 강제 클릭
            driver.execute_script("arguments[0].click();", yes_btn)
        # 모달이 사라질 때까지 잠깐 대기(완전히 닫힘 보장)
        wait.until(EC.invisibility_of_element_located((By.ID, "new-fish-available-modal")))
    except TimeoutException:
        # 모달이 안 뜬 경우
        pass


def close_modal(driver):
    try:
        modal = driver.find_element(By.CSS_SELECTOR, ".modal.upcoming-windows.active")
        if modal:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ESCAPE)
            WebDriverWait(driver, 3).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal.upcoming-windows.active"))
            )
    except Exception:
        pass

def extract_availability(row, driver):
    try:
        data_id = int(row.get_attribute("data-id"))
        calendar_btn = row.find_element(By.CSS_SELECTOR, ".upcoming-windows-button")

        close_modal(driver)
        ActionChains(driver).move_to_element(calendar_btn).pause(0.05).click().perform()

        # 모달이 '열렸는지'만 대기 (아이템 존재 대기 X)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal.upcoming-windows.active"))
        )

        # 파싱 시도: 비어 있으면 [] 반환
        try:
            root = driver.find_element(By.CSS_SELECTOR, ".modal.upcoming-windows.active")
            items = root.find_elements(By.CSS_SELECTOR, ".upcoming-windows-grid .window-start")
            if items:
                upcoming_windows = extract_modal_data_selenium(driver)  # 기존 함수 사용
            else:
                upcoming_windows = []  # 아이템 없음 → 빈 배열로 수집
        finally:
            close_modal(driver)

        return {"id": data_id, "upcoming_windows": upcoming_windows, "parsed_at": datetime.now(KST)}
    except Exception:
        return None
        

@task()
def fetch_and_upsert_fish_full_uptime():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(*VIEWPORT)
    driver.get(URL)
    handle_new_fish_modal(driver)
    
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#fishes tbody")))
    time.sleep(1.0)

    rows = driver.find_elements(By.CSS_SELECTOR, 'table#fishes tbody tr.fish-entry')
    results = []
    for row in rows:
        try:
            # uptime 요소 없으면 스킵
            try:
                row.find_element(By.CSS_SELECTOR, '.fish-availability-uptime')
            except NoSuchElementException:
                continue

            # 달력 버튼 없으면 스킵
            try:
                row.find_element(By.CSS_SELECTOR, ".upcoming-windows-button")
            except NoSuchElementException:
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", row)
            time.sleep(0.05)

            data = extract_availability(row, driver)
            if data:
                results.append(data)

        except Exception:
            continue
    driver.quit()

    hook = PostgresHook(postgres_conn_id="postgres")
    with hook.get_conn() as conn, conn.cursor() as cur:
        for row in results:
            cur.execute("""
                INSERT INTO fish_full_uptime (id, upcoming_windows, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    upcoming_windows = EXCLUDED.upcoming_windows,
                    updated_at = EXCLUDED.updated_at
            """, (
                row["id"],
                json.dumps(row["upcoming_windows"]),
                row["parsed_at"].replace(tzinfo=None)
            ))
        conn.commit()

with DAG(
    dag_id="fetch_fish_full_uptime",
    start_date=datetime(2025, 7, 31),
    schedule="10 * * * *",
    catchup=False,
    tags=["data", "carbuncleplushy",'selenium'],
    description="물고기 업타임 캘린더 수집",
) as dag:
    fetch_and_upsert_fish_full_uptime()