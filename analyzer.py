import cv2
import pytesseract
import re
from datetime import datetime

# 全域變數：用來記錄「消失前」的最後有效時間
last_valid_time1 = None
last_valid_time2 = None
last_text1 = ""
last_text2 = ""
is_tracking = False

def time_to_seconds(time_str):
    """將 M:SS, MM:SS, H:MM:SS 轉為總秒數，方便計算差值"""
    try:
        # 只保留數字與冒號，去除雜訊
        clean_str = re.sub(r'[^\d:]', '', time_str)
        parts = clean_str.split(':')
        
        if len(parts) == 2: # M:SS 或 MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return None

def preprocess_image(img):
    """影像前處理：放大圖片並轉黑白，大幅提升辨識小字體的準確度"""
    # 放大 3 倍
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    # 轉灰階
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 二值化 (黑白)
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return binary

def process_screenshot(img_numpy):
    """接收截圖並進行分析的主函數"""
    global last_valid_time1, last_valid_time2, last_text1, last_text2, is_tracking
    
    # 1. 根據座標裁切圖片 (注意 numpy 的切片順序是[y:y+h, x:x+w])
    # 固定時間：(1170,146,52,12)
    crop1 = img_numpy[146:146+12, 1170:1170+52]
    # 持續增加的時間：(1105,117,113,28)
    crop2 = img_numpy[117:117+28, 1105:1105+113]

    # 2. 影像前處理
    img1_processed = preprocess_image(crop1)
    img2_processed = preprocess_image(crop2)

    # 3. 進行 OCR 辨識 (限定只辨識數字和冒號，提升準確率)
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:'
    text1 = pytesseract.image_to_string(img1_processed, config=custom_config).strip()
    text2 = pytesseract.image_to_string(img2_processed, config=custom_config).strip()

    # 4. 轉換為秒數
    sec1 = time_to_seconds(text1)
    sec2 = time_to_seconds(text2)

    # 5. 邏輯判斷
    if sec1 is not None and sec2 is not None:
        # 如果兩邊都抓得到數字，代表正在計時中，更新「最後已知狀態」
        last_valid_time1 = sec1
        last_valid_time2 = sec2
        last_text1 = text1
        last_text2 = text2
        is_tracking = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 追蹤中... 固定時間:{text1}, 持續時間:{text2}")

    elif is_tracking and sec1 is None and sec2 is None:
        # 如果之前在追蹤，但現在兩邊的數字同時消失了 (辨識不到)
        print("\n" + "="*40)
        print(f"🚨 檢測到時間同時消失！")
        print(f"消失前 固定時間 (A): {last_text1} ({last_valid_time1} 秒)")
        print(f"消失前 持續時間 (B): {last_text2} ({last_valid_time2} 秒)")
        
        # 計算時間差 (取絕對值)
        diff_seconds = abs(last_valid_time2 - last_valid_time1)
        
        # 將差值轉回 MM:SS 格式
        m, s = divmod(diff_seconds, 60)
        print(f"⏱️ 兩者相差: {m}分 {s}秒 ({diff_seconds} 秒)")
        print("="*40 + "\n")
        
        # 寫入記錄檔
        with open("time_record.csv", "a", encoding="utf-8") as f:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{now}],{last_text1},{last_text2},{diff_seconds}\n")
        
        # 重置狀態，等待下一次按下按鈕
        is_tracking = False
        last_valid_time1 = None
        last_valid_time2 = None