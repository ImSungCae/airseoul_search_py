import time
import random
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib3
import ssl
from selenium_stealth import stealth
import undetected_chromedriver as uc
from datetime import datetime
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSL 경고 무시 설정
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# 이메일 설정 (실제 정보로 변경 필요)
EMAIL_SENDER = "spr3133@gmail.com"
EMAIL_PASSWORD = "mnzd syor oick agsy"  # Gmail의 경우 앱 비밀번호 사용
EMAIL_RECEIVER = "lschmhj@naver.com"

def random_delay(min_seconds=0.5, max_seconds=3.0):
    """인간과 유사한 랜덤 지연시간 생성"""
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"랜덤 지연: {delay:.2f}초")
    time.sleep(delay)

def setup_driver():
    """CloudFlare 우회에 최적화된 드라이버 설정"""
    try:
        # 방법 1: undetected_chromedriver 사용 (권장)
        options = uc.ChromeOptions()
        
        # 사용자 프로필 설정 (선택 사항)
        # options.add_argument('--user-data-dir=C:\\Path\\To\\Chrome\\Profile')
        # options.add_argument('--profile-directory=Default')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--ignore-certificate-errors')
        
        # 실제 사용자 에이전트 설정
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        logger.info("undetected_chromedriver로 웹드라이버 초기화 중...")
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(60)
        logger.info("웹드라이버 초기화 완료")
        
        return driver
        
    except Exception as e:
        logger.error(f"undetected_chromedriver 초기화 실패: {e}")
        logger.info("일반 셀레니움으로 대체 시도...")
        
        # 방법 2: 일반 셀레니움 + stealth (대체 방법)
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Stealth 설정
        stealth(driver,
            languages=["ko-KR", "ko", "en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        # 자동화 흔적 제거를 위한 JavaScript 실행
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 추가 탐지 방지 스크립트
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """
        })
        
        return driver

def handle_cloudflare_challenge(driver, max_wait=120):
    """CloudFlare 챌린지 대기 및 처리"""
    logger.info("CloudFlare 챌린지 확인 중...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if "Just a moment" in driver.page_source or "Checking your browser" in driver.page_source:
            logger.info("CloudFlare 챌린지 감지됨, 대기 중...")
            time.sleep(5)  # 더 긴 대기 시간
        else:
            logger.info("CloudFlare 챌린지 통과 또는 감지되지 않음")
            return True
    
    logger.error(f"CloudFlare 챌린지 타임아웃: {max_wait}초 경과")
    return False

def send_email(subject, message):
    """이메일 발송 함수"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info("이메일 전송 성공!")
        return True
    except Exception as e:
        logger.error(f"이메일 전송 실패: {e}")
        return False

def check_reservation_availability(driver):
    """항공권 예약 가능 여부 확인"""
    flight_selectors = [
        "#Dep_Flight > tr:nth-child(1) > td:nth-child(5)",
        "#Dep_Flight > tr:nth-child(3) > td:nth-child(5)",
        "#Arr_Flight > tr:nth-child(1) > td:nth-child(5)",
        "#Arr_Flight > tr:nth-child(3) > td:nth-child(5)"
    ]
    
    available_flights = []
    all_unavailable = True
    
    # 각 항공편 확인
    for i, selector in enumerate(flight_selectors):
        try:
            element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            flight_type = "출발" if i < 2 else "도착"
            flight_num = (i % 2) + 1
            
            if "tbl-price" in element.get_attribute("class"):
                available_flights.append(f"{flight_type} 항공편 {flight_num}")
                all_unavailable = False
                logger.info(f"{flight_type} 항공편 {flight_num}: 예약 가능")
            else:
                logger.info(f"{flight_type} 항공편 {flight_num}: 예약 불가")
        except Exception as e:
            logger.warning(f"항공편 {i+1} 확인 실패: {e}")
    
    # 예약 가능한 항공편이 있으면 이메일 발송
    if not all_unavailable:
        # 현재 날짜 정보 가져오기
        try:
            date_info_dep = driver.find_element(By.ID, "txtDepBookingDate").get_attribute("value")
            date_info_arr = driver.find_element(By.ID, "txtArrBookingDate").get_attribute("value")
        except:
            date_info_dep = "출발 날짜 정보 확인 실패"
            date_info_arr = "도착 날짜 정보 확인 실패"
        
        # 스크린샷 저장
        try:
            # screenshot 폴더가 없으면 생성
            screenshot_dir = "screenshot"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
                logger.info(f"스크린샷 폴더 생성: {screenshot_dir}")
            
            # 파일명 생성 및 경로 지정
            screenshot_filename = f"항공권_검색_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
            
            # 스크린샷 저장
            driver.save_screenshot(screenshot_path)
            logger.info(f"예약 가능 화면 캡처 저장: {screenshot_path}")
        except Exception as e:
            logger.warning(f"스크린샷 저장 실패: {e}")
        
        # 이메일 발송
        subject = f"[에어서울] 항공권 예약 가능 알림 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        message = f"""
에어서울 항공권 예약 가능 알림입니다.

검색 날짜: {date_info_dep} ~ {date_info_arr}
예약 가능한 항공편:
{', '.join(available_flights)}

지금 예약하세요!
https://flyairseoul.com/CW/ko/main.do
"""
        send_email(subject, message)
    
    return all_unavailable

def change_next_date(driver):
    """다음 날짜로 변경"""
    try:
        # 캘린더 아이콘 클릭
        logger.info("캘린더 아이콘 클릭...")
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#txtDepBookingDateButton"))
        ).click()
        random_delay(1, 2)
        
        # 현재 선택된 출발일 다음 날짜 선택
        logger.info("다음 출발일 선택...")
        try:
            # 먼저 rangeBegin(현재 출발일) 클래스 요소 찾기
            range_begin = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "td.rangeBegin"))
            )
            
            # 다음 td 요소 찾기 (JavaScript 사용)
            driver.execute_script("""
                var rangeBegin = document.querySelector('td.rangeBegin');
                if (rangeBegin) {
                    // 다음 셀 확인
                    var nextCell = rangeBegin.nextElementSibling;
                    
                    // 다음 셀이 없거나 disabled인 경우 (행의 마지막 셀인 경우)
                    if (!nextCell || nextCell.classList.contains('disabled')) {
                        // 현재 행(tr)의 다음 행 찾기
                        var nextRow = rangeBegin.parentElement.nextElementSibling;
                        if (nextRow) {
                            // 다음 행의 첫 번째 셀 선택
                            nextCell = nextRow.querySelector('td:not(.disabled)');
                        }
                    }
                    
                    // 다음 셀이 있으면 클릭
                    if (nextCell && !nextCell.classList.contains('disabled')) {
                        nextCell.click();
                    }
                }
            """)
            random_delay(1, 2)
        except Exception as e:
            logger.error(f"출발일 변경 실패: {e}")
        
        # 현재 선택된 도착일 다음 날짜 선택
        logger.info("다음 도착일 선택...")
        try:
            # 먼저 rangeEnd(현재 도착일) 클래스 요소 찾기
            range_end = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "td.rangeEnd"))
            )
            
            # 종료 조건 확인: data-date 속성이 "20251011"인지
            if range_end.get_attribute("data-date") == "20251011":
                logger.info("종료 날짜(2025-10-11)에 도달했습니다. 검색을 종료합니다.")
                return True  # 종료 조건 충족
            
            # 다음 td 요소 찾기 (JavaScript 사용)
            driver.execute_script("""
                var rangeEnd = document.querySelector('td.rangeEnd');
                if (rangeEnd) {
                    var nextCell = rangeEnd.nextElementSibling;
                    if (nextCell && !nextCell.classList.contains('disabled')) {
                        nextCell.click();
                    }
                }
            """)
            random_delay(1, 2)
        except Exception as e:
            logger.error(f"도착일 변경 실패: {e}")
        
        # 닫기 버튼 클릭
        logger.info("달력 닫기...")
        try:
            close_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#bookingDateLayer > div > div > div.rsDatePickerCloseArea > div.legendInfo > div.rsCalendarClose > button"))
            )
            close_button.click()
        except:
            # 버튼을 찾지 못하면 JavaScript로 시도
            driver.execute_script("""
                var closeButton = document.querySelector("#bookingDateLayer > div > div > div.rsDatePickerCloseArea > div.legendInfo > div.rsCalendarClose > button");
                if (closeButton) {
                    closeButton.click();
                }
            """)
        
        random_delay(1, 2)
        
        # 조회 버튼 클릭
        logger.info("조회 버튼 클릭...")
        try:
            search_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#goItinerary"))
            )
            search_button.click()
        except:
            # 버튼을 찾지 못하면 JavaScript로 시도
            driver.execute_script("document.getElementById('goItinerary').click();")
        
        # 결과 로딩 기다리기
        random_delay(4, 5)
        
        # CloudFlare 챌린지 확인
        handle_cloudflare_challenge(driver)
        
        # 컨펌 창 처리
        try:
            confirmPopups = driver.find_elements(By.ID, "LayerConfirm")
            if confirmPopups and confirmPopups[0].is_displayed():
                confirmPopups[0].click()
            else:
                # JavaScript로 컨펌 창 처리 시도
                driver.execute_script("""
                    if (document.getElementById('LayerConfirm')) {
                        document.getElementById('LayerConfirm').click();
                    }
                    
                    if (typeof fn_ClickIntInformationBtn === 'function') {
                        fn_ClickIntInformationBtn();
                    }
                """)
        except:
            pass
        
        random_delay(1, 2)
        return False  # 아직 종료 조건 미충족
    except Exception as e:
        logger.error(f"날짜 변경 중 오류 발생: {e}")
        return False

def initial_search(driver):
    """초기 검색 수행"""
    try:
        # 에어서울 메인 페이지 접속
        logger.info("에어서울 사이트에 접속 중...")
        driver.get('https://flyairseoul.com/CW/ko/main.do')
        
        # CloudFlare 챌린지 처리
        if not handle_cloudflare_challenge(driver):
            logger.error("CloudFlare 챌린지를 통과하지 못했습니다.")
            return False
        
        # 페이지 타이틀 확인
        logger.info(f"페이지 제목: {driver.title}")
        random_delay(2, 4)
        
        # 팝업 처리
        try:
            popups = driver.find_elements(By.CSS_SELECTOR, "#wrap > div.event_popup > div.ep > div.bottom > a.ep_close.ep_nottoday")
            if popups:
                logger.info("팝업 닫기 시도 중...")
                popups[0].click()
                random_delay()
            else:
                logger.info("닫을 팝업이 없습니다.")
        except Exception as e:
            logger.warning(f"팝업 처리 중 오류: {e}")
        
        # 출발지 선택
        logger.info("출발지 입력란 클릭...")
        departure_input = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "txtDepAirport"))
        )
        random_delay(1, 2)
        departure_input.click()
        random_delay()
        
        logger.info("서울/인천(ICN) 선택 중...")
        departure_seoul = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#departureAirportList > div:nth-child(1) > ul > li:nth-child(1) > button"))
        )
        random_delay(1, 2)
        departure_seoul.click()
        random_delay()
        
        # 도착지 선택
        logger.info("후쿠오카(FUK) 선택 중...")
        arrival_fukuoka = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#arrivalAirportList > div:nth-child(1) > ul > li:nth-child(3) > button"))
        )
        random_delay(1, 2)
        arrival_fukuoka.click()
        random_delay()
        
        # 날짜 선택
        target_month = "2025.10"
        try:
            # 현재 표시된 월 확인
            current_month_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerWrap.rsDatePickerWrapOutbound.on > div > div > div.title > div.displayDate"))
            )
            
            # 다음 달 버튼
            next_month_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerWrap.rsDatePickerWrapOutbound.on > div > div > div.title > div.nextMonth"))
            )
            
            # 현재 달 확인 후 목표 월까지 클릭
            current_month = current_month_element.text
            logger.info(f"현재 표시된 월: {current_month}")
            
            while current_month != target_month:
                random_delay(1, 2)
                next_month_button.click()
                random_delay()
                
                # 업데이트된 현재 월 다시 가져오기
                current_month = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerWrap.rsDatePickerWrapOutbound.on > div > div > div.title > div.displayDate"))
                ).text
                
                logger.info(f"다음 달로 이동: {current_month}")
                
                # 무한 루프 방지를 위한 안전장치
                if current_month == target_month:
                    logger.info(f"목표 월 {target_month}에 도달했습니다.")
                    break
        except Exception as e:
            logger.error(f"날짜 선택 중 오류 발생: {e}")
        
        # 출발일 선택
        try:
            logger.info("출발일 선택 중...")
            
            # 날짜 요소들을 전부 찾아서 클릭 가능한 첫 번째 목요일 선택
            available_dates = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerWrap.rsDatePickerWrapOutbound.on > div > div > div.tableWrap > table > tbody > tr > td:not(.disabled)"))
            )
            
            # 목요일 찾기
            for date in available_dates:
                if "weekThu" in date.get_attribute("class"):
                    random_delay(1, 2)
                    date.click()
                    logger.info("출발일 목요일을 선택했습니다.")
                    break
            
            random_delay()
        except Exception as e:
            logger.error(f"출발일 선택 중 오류 발생: {e}")
        
        # 귀국일 선택
        try:
            logger.info("귀국일 선택 중...")
            
            # 귀국 날짜 요소들을 전부 찾아서 클릭 가능한 첫 번째 월요일 선택
            return_available_dates = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerWrap.rsDatePickerWrapReturn > div > div > div.tableWrap > table > tbody > tr > td:not(.disabled)"))
            )
            
            # 월요일 찾기
            for date in return_available_dates:
                if "weekMon" in date.get_attribute("class"):
                    random_delay(1, 2)
                    date.click()
                    logger.info("귀국일 월요일을 선택했습니다.")
                    break
            
            random_delay()
        except Exception as e:
            logger.error(f"귀국일 선택 중 오류 발생: {e}")
        
        # 달력 닫기
        try:
            logger.info("달력 닫기 시도...")
            
            try:
                close_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#content > div.main_cont > div.quick_reservation.easy_quick_reservation > div > div > div.bottom > div.date > div.rtCalendarWrap > div > div > div.rsDatePickerCloseArea > div.legendInfo > div.rsCalendarClose > span.layerClose.layer-close"))
                )
                random_delay(1, 2)
                close_button.click()
                logger.info("달력 닫기 버튼 클릭 성공")
            except:
                logger.info("달력 닫기 버튼을 찾을 수 없어 JavaScript로 시도합니다.")
                driver.execute_script("""
                    var closeButtons = document.querySelectorAll(".layerClose.layer-close");
                    for(var i=0; i<closeButtons.length; i++) {
                        closeButtons[i].click();
                    }
                """)
                logger.info("JavaScript로 달력 닫기 시도 완료")
            
            random_delay()
        except Exception as e:
            logger.error(f"달력 닫기 중 오류 발생: {e}")
            
        # 성인 인원수 증가
        try:
            increase_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "increaseADT"))
            )
            random_delay(1, 2)
            increase_button.click()
            logger.info("성인 인원수 증가 버튼 클릭")
            random_delay()
        except Exception as e:
            logger.warning(f"성인 인원수 증가 버튼 오류: {e}")
            
        # 조회하기 버튼 클릭
        logger.info("항공권 검색 버튼 클릭...")
        try:
            search_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "goItinerary"))
            )
            random_delay(1, 2)
            search_button.click()
            logger.info("항공권 검색 버튼을 클릭했습니다.")
        except Exception as e:
            logger.error(f"항공권 검색 버튼 클릭 중 오류 발생: {e}")
            logger.info("JavaScript를 사용하여 검색 버튼 클릭 시도...")
            driver.execute_script("document.getElementById('goItinerary').click();")
        
        # 검색 결과 페이지 로딩 기다리기
        logger.info("검색 결과 로딩 중...")
        random_delay(3, 5)
        
        # CloudFlare 챌린지 다시 확인
        handle_cloudflare_challenge(driver)
        
        # 컨펌 창 처리
        try:
            logger.info("컨펌 창 확인 중...")
            confirmPopups = driver.find_elements(By.ID, "LayerConfirm")
            
            if confirmPopups and confirmPopups[0].is_displayed():
                random_delay(1, 2)
                confirmPopups[0].click()
                logger.info("컨펌 창 클릭 성공")
            else:
                logger.info("컨펌 창이 보이지 않음, JavaScript 실행 시도...")
                # 여러 방법으로 시도
                driver.execute_script("""
                    // 방법 1: ID로 직접 클릭
                    if(document.getElementById('LayerConfirm')) {
                        document.getElementById('LayerConfirm').click();
                    }
                    
                    // 방법 2: 함수 직접 호출
                    if(typeof fn_ClickIntInformationBtn === 'function') {
                        fn_ClickIntInformationBtn();
                    }
                    
                    // 방법 3: 다양한 확인 버튼 찾아서 클릭
                    var confirmButtons = document.querySelectorAll('.btnConfirm, .btn_confirm, .btn-confirm, [id*="confirm"], [class*="confirm"]');
                    for(var i=0; i<confirmButtons.length; i++) {
                        confirmButtons[i].click();
                    }
                """)
                logger.info("JavaScript를 통한 컨펌 창 처리 시도 완료")
            
            random_delay(3, 5)
        except Exception as e:
            logger.warning(f"컨펌 창 처리 중 오류: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"초기 검색 중 오류 발생: {e}")
        return False

def main():
    driver = None
    try:
        driver = setup_driver()
        
        # 초기 검색 수행
        if not initial_search(driver):
            logger.error("초기 검색에 실패했습니다.")
            return
        
        # 종료 조건 도달할 때까지 반복
        search_count = 0
        while True:
            search_count += 1
            logger.info(f"====== 검색 #{search_count} 시작 ======")
            
            # 예약 가능 여부 확인
            all_unavailable = check_reservation_availability(driver)
            
            # 모든 항공편이 예약 불가능하면 다음 날짜로 변경
            if all_unavailable:
                logger.info("모든 항공편이 예약 불가합니다. 다음 날짜로 변경합니다.")
                is_end_date = change_next_date(driver)
                
                # 종료 날짜에 도달했는지 확인
                if is_end_date:
                    logger.info("지정된 종료 날짜(2025-10-11)에 도달했습니다. 프로그램을 종료합니다.")
                    break
            else:
                # 예약 가능한 항공편 발견, 이메일 발송 후 계속 진행
                logger.info("예약 가능한 항공편 발견! 이메일을 발송했습니다.")
                
                # 계속 다음 날짜 확인
                random_delay(2, 3)
                is_end_date = change_next_date(driver)
                if is_end_date:
                    break
            
            # 매 10회 검색마다 페이지 새로고침
            if search_count % 10 == 0:
                logger.info("주기적 페이지 새로고침 수행...")
                try:
                    driver.refresh()
                    random_delay(3, 5)
                    handle_cloudflare_challenge(driver)
                except Exception as e:
                    logger.warning(f"페이지 새로고침 중 오류: {e}")
    
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
    
    finally:
        if driver:
            logger.info("브라우저 종료 중...")
            driver.quit()
            logger.info("브라우저가 종료되었습니다.")

if __name__ == "__main__":
    main()