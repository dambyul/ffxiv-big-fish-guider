from airflow.sdk import DAG, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timezone, timedelta
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

URL = "https://ff14fish.carbuncleplushy.com/"
VIEWPORT = (1400, 1000)
KST = timezone(timedelta(hours=9))

def ms_to_kst_iso(ms: Optional[int]) -> Optional[str]:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(KST).isoformat(timespec="seconds")

def to_int_or_none(v):
    try:
        return int(v) if v not in (None, "", "null") else None
    except Exception:
        return None

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

def extract_availability(row):
    try:
        data_id = int(row.get_attribute("data-id"))

        # 업타임: 없으면 None, 실제 100.0인 경우만 스킵
        uptime = None
        try:
            t = row.find_element(By.CSS_SELECTOR, '.fish-availability-uptime').text.strip()
            uptime = float(t) if t else None
        except NoSuchElementException:
            uptime = None

        if uptime is not None and uptime >= 100.0:
            return None

        class_list = row.get_attribute("class") or ""
        is_active = 'fish-active' in class_list

        # 현재창 시작 (active가 아니면 표에 'in N hours'로 표시됨)
        current_start = None
        if not is_active:
            try:
                curr = row.find_element(By.CSS_SELECTOR, '.fish-availability-current')
                ms = to_int_or_none(curr.get_attribute("data-val"))
                current_start = ms_to_kst_iso(ms) if ms is not None else None
            except NoSuchElementException:
                current_start = None

        # 현재창 종료/다음창 시작
        current_end = None
        next_start = None
        try:
            next_span = row.find_element(By.CSS_SELECTOR, '.fish-availability-upcoming')
            prev_ms = to_int_or_none(next_span.get_attribute("data-prevclose"))
            val_ms  = to_int_or_none(next_span.get_attribute("data-val"))
            current_end = ms_to_kst_iso(prev_ms) if prev_ms is not None else None
            next_start  = ms_to_kst_iso(val_ms)  if val_ms  is not None else None
        except NoSuchElementException:
            pass

        return {
            "id": data_id,
            "uptime_percent": uptime,
            "current_start": current_start,
            "current_end": current_end,
            "next_start": next_start,
        }

    except Exception as e:
        print(f"[SKIP {row.get_attribute('data-id')}] {e}")
        return None
    
@task()
def fetch_and_upsert_fish_uptime_list():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(*VIEWPORT)
    driver.get(URL)
    handle_new_fish_modal(driver)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table#fishes tbody"))
    )
    time.sleep(1.0)

    rows = driver.find_elements(By.CSS_SELECTOR, 'table#fishes tbody tr.fish-entry:not(.fish-intuition-row)')
    results = []

    for row in rows:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", row)
            time.sleep(0.05)
            data = extract_availability(row)
            if data:
                results.append(data)
        except Exception:
            continue

    driver.quit()

    hook = PostgresHook(postgres_conn_id="postgres")
    with hook.get_conn() as conn, conn.cursor() as cur:
        for row in results:
            cur.execute("""
                INSERT INTO fish_uptime (id, uptime_percent, current_start, current_end, next_start, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    uptime_percent = EXCLUDED.uptime_percent,
                    current_start = EXCLUDED.current_start,
                    current_end = EXCLUDED.current_end,
                    next_start = EXCLUDED.next_start,
                    updated_at = NOW()
            """, (
                row["id"],
                row["uptime_percent"],
                row["current_start"],
                row["current_end"],
                row["next_start"],
            ))
        conn.commit()

with DAG(
    dag_id="fetch_fish_uptime_list",
    start_date=datetime(2025, 7, 31),
    schedule = "*/5 * * * *",
    catchup=False,
    tags=["data", "carbuncleplushy", "selenium"],
    description="물고기 업타임 리스트 수집",
) as dag:
    fetch_and_upsert_fish_uptime_list()
