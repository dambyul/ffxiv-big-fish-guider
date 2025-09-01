from airflow.sdk import DAG, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import time

VIEWPORT = (1400, 1000)
BASE_URL = "https://ffxivteamcraft.com/db/ko/item"

def wait_for_stat_loaded(card, title, timeout=30, poll_interval=0.5):
    def extract_stat_value():
        try:
            stat = card.find_element(
                By.XPATH,
                f'.//div[contains(@class, "ant-statistic-title") and text()="{title}"]/following-sibling::div'
            )
            value_int = stat.find_element(By.CLASS_NAME, "ant-statistic-content-value-int").text.strip()
            try:
                value_decimal = stat.find_element(By.CLASS_NAME, "ant-statistic-content-value-decimal").text.strip()
            except NoSuchElementException:
                value_decimal = ""
            combined = value_int + value_decimal
            combined = combined.replace("s", "").strip()

            if re.match(r"^\d+(\.\d+)?$", combined):
                return float(combined)
        except NoSuchElementException:
            pass
        return None

    if title == "Average":
        value = extract_stat_value()
        if value is None:
            print(f"평균 값 없음 (null 처리)")
        return value

    start = time.time()
    while time.time() - start < timeout:
        value = extract_stat_value()
        if value is not None:
            return value
        time.sleep(poll_interval)

    print(f"{title} 값 로딩 실패")
    return None


@task()
def fetch_and_upsert_bite_time():
    hook = PostgresHook(postgres_conn_id="postgres")
    with hook.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT distinct fish_id FROM v_fish_bait WHERE step_no <> 1")
        fish_ids = [row[0] for row in cur.fetchall()]

    print(f"[INFO] 총 {len(fish_ids)}개 ID 수집 대상")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    results = []
    modal_checked = False 

    for fish_id in fish_ids:
        url = f"{BASE_URL}/{fish_id}"
        driver.get(url)
        wait = WebDriverWait(driver, 30)

        if not modal_checked:
            try:
                close_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ant-modal-close")))
                close_btn.click()
                print("[INFO] 초기 모달 닫기 완료")
            except TimeoutException:
                print("[INFO] 모달 없음 또는 자동 닫힘")
            modal_checked = True

        try:
            wait.until(EC.presence_of_element_located((
                By.XPATH, '//div[contains(@class, "ant-card-head-title") and contains(text(), "Bite time")]'
            )))
            card = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-fish-bite-times nz-card")))

            result = {
                "id": fish_id,
                "min_bite_time": wait_for_stat_loaded(card, "Minimum"),
                "max_bite_time": wait_for_stat_loaded(card, "Maximum"),
                "avg_bite_time": wait_for_stat_loaded(card, "Average"),
            }
            print(f"[DEBUG] {fish_id} → {result}")

            if result["min_bite_time"] is None or result["max_bite_time"] is None:
                print(f"[WARN] {result['id']} → min/max 값 없음, skip")
                continue   

            results.append(result)

        except TimeoutException:
            print(f"[WARN] {fish_id} 페이지 로딩 실패")
            continue

    driver.quit()

    with hook.get_conn() as conn, conn.cursor() as cur:
        for row in results:
            cur.execute("""
                INSERT INTO fish_bite_time (id, min_bite_time, max_bite_time, avg_bite_time, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    min_bite_time = EXCLUDED.min_bite_time,
                    max_bite_time = EXCLUDED.max_bite_time,
                    avg_bite_time = EXCLUDED.avg_bite_time,
                    updated_at = NOW()
            """, (
                row["id"],
                row["min_bite_time"],
                row["max_bite_time"],
                row["avg_bite_time"]
            ))
        conn.commit()

with DAG(
    dag_id="fetch_fish_bite_time",
    start_date=datetime(2025, 7, 31),
    schedule="0 */6 * * *",
    catchup=False,
    tags=["data", "teamcraft", "selenium"],
    description="팀크래프트 입질 시간 수집",
) as dag:
    fetch_and_upsert_bite_time()
